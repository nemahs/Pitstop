import json
import logging
import time
from typing import Any, Callable, Sequence, cast

from more_itertools import partition
from valkey import Valkey

from ..data.esi import ESI, ESIError
from ..data.esi.corporation import (
    ESIContract,
    get_corp_contract_items,
    get_corp_contracts,
)
from ..data.esi.esi import get_bulk_names, get_structure_names
from ..data.typing import AccessToken, RefreshToken
from .typing import *

valkey_client = Valkey(host="valkey")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def pull_contracts(esi: ESI, corp_id: CorpID):
    while True:
        user: Any | None = valkey_client.srandmember("characters")
        if user:
            cast(bytes, user)
            user_id = UserID(BaseID(int(user.decode())))
            logger.info("Using user %d for contracts", user_id)

            logger.debug("Getting basic contract data for corp")
            contracts = get_basic_contract_data(esi, user_id, corp_id)

            logger.debug("Fetching names")
            contracts = get_names(esi, contracts, user_id)

            contract_ids: list[ContractID] = [
                ContractID(BaseID(contract["contract_id"]))
                for contract in contracts
                if contract["status"] in ("outstanding", "in_progress")
                and (int(contract["assignee_id"]) == corp_id or int(contract["issuer_id"]) == corp_id)
            ]

            logger.debug("Initial filter: %s", str(contract_ids))

            with valkey_client.pipeline(False) as pipeline:
                [pipeline.exists(f"contracts:{id}") for id in contract_ids]
                missing_items: list[ContractID] = [
                    id for id, found in zip(contract_ids, pipeline.execute()) if found == 0
                ]

            logger.debug("Contracts to fetch items for: %s", str(missing_items))
            with valkey_client.pipeline() as pipeline:
                for id in missing_items:
                    access_token = get_key(esi, user_id)  # Reget key in case it expired

                    try:
                        logger.debug("Getting items for contract %d", id)
                        items = get_corp_contract_items(corp_id, id, access_token)
                    except ESIError:
                        logger.error("ESI ERROR ON CONTRACT %d", id)
                        continue

                    item_names = cached_lookup("names", "type_id", items, get_bulk_names)
                    [item.update({"name": item_names.get(item["type_id"], "Unknown")}) for item in items]

                    pipeline.set(
                        f"contracts:{id}",
                        json.dumps(items),
                    )
                pipeline.execute(raise_on_error=True)
            valkey_client.set("contracts", json.dumps(contracts), ex=600)

            logger.info("Waiting 5 minutes")  # TODO: Properly wait for cache expiry to get data AFAP
            time.sleep(300)


def get_basic_contract_data(esi: ESI, user_id: UserID, corp_id: CorpID) -> list[ESIContract]:
    access_token = get_key(esi, user_id)
    contracts = get_corp_contracts(corp_id, access_token)
    return contracts


def get_names(esi: ESI, contracts: Sequence[ESIContract], user_id: UserID) -> Sequence[EnrichedContract]:
    output: Sequence[EnrichedContract] = cast(Sequence[EnrichedContract], contracts)

    issuer_names = cached_lookup("names", "issuer_id", contracts, get_bulk_names)
    [
        contract.update({"issuer_name": issuer_names.get(BaseID(contract["issuer_id"]), "Unknown")})
        for contract in output
    ]

    assignee_names = cached_lookup("names", "assignee_id", contracts, get_bulk_names)
    [
        contract.update({"assignee_name": assignee_names.get(BaseID(contract["assignee_id"]), "Unknown")})
        for contract in output
    ]

    access_token = get_key(esi, user_id)
    structure_names = cached_lookup(
        "names", "start_location_id", contracts, lambda x: get_structure_names(x, access_token)
    )
    [
        contract.update({"location_name": structure_names.get(BaseID(contract["start_location_id"]), "Unknown")})
        for contract in output
        if "start_location_id" in contract
    ]

    return output


type LookupFunction = Callable[[list[BaseID]], dict[BaseID, str]]


def cached_lookup(
    prefix: str, attr: str, contracts: Sequence[ESIContract], lookup_func: LookupFunction
) -> dict[BaseID, str]:
    """Look up names for a set of IDs, caching the results in Valkey.

    :param prefix: Valkey prefix for caching
    :param attr: Attribute in contracts to use for lookup. Must map to an ID
    :param contracts: Contract list to look up names for
    :param lookup_func: Function to lookup unknown names
    :return: Mapping of attr IDs to their names
    """
    unknown_ids, known_ids = partition(
        lambda x: valkey_client.exists(f"{prefix}:{x}"), {contract[attr] for contract in contracts}
    )

    unknown_ids = list(unknown_ids)
    known_ids = list(known_ids)

    logger.debug("%d known %s ids, %d unknown %s ids", len(known_ids), attr, len(unknown_ids), attr)

    output = {id: valkey_client.get(f"{prefix}:{id}").decode() for id in known_ids}  # type: ignore

    if unknown_ids:
        new_names = lookup_func(unknown_ids)
        output.update(new_names)
        for id, name in new_names.items():
            valkey_client.set(f"{prefix}:{id}", name)
            logger.debug("Set name for %d", id)

    return output


def get_key(esi: ESI, user_id: UserID) -> AccessToken:
    """Get the access token for a user, refreshing it if necessary.

    :param esi: ESI object to user for refreshing token if needed
    :param user_id: UserID of the user to get the token for

    :return: ESI AccessToken for user
    """
    if (
        valkey_client.exists(f"{user_id}:access_token")
        and (remaining_ttl := int(valkey_client.ttl(f"{user_id}:access_token"))) > 100  # type: ignore
    ):
        data = valkey_client.get(f"{user_id}:access_token")
        assert isinstance(data, bytes)
        logger.debug("%d seconds left in access token", remaining_ttl)
        return AccessToken(data.decode())

    refresh_token_data = valkey_client.get(f"{user_id}:refresh_token")
    assert isinstance(refresh_token_data, bytes)
    refresh_token = RefreshToken(refresh_token_data.decode())

    token_data = esi.refresh_tokens(refresh_token)
    valkey_client.set(f"{user_id}:access_token", token_data.access_token, ex=token_data.expiry)

    return token_data.access_token
