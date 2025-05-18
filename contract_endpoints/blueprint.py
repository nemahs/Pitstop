import itertools
import json
import logging
from datetime import datetime
from string import Template
from typing import Any, cast
from collections.abc import Callable

from valkey import Valkey
from flask import Blueprint

from .dataclasses import *
from .typing import *
from .filters import filter_functions
from ..data.esi import ESI
from .stations import create_station_blueprint, STATION_KEY

logger = logging.getLogger(__name__)
CONTRACT_LIST_KEY = "contracts"
CONTRACT_ITEMS_KEY = Template(f"{CONTRACT_LIST_KEY}:$id")
ITEM_NAME_KEY = Template("names:$id")

def get_outstanding_contracts(corp_id: CorpID, valkey_client: Valkey) -> list[Contract]:
    contract_data: Any | None = valkey_client.get(CONTRACT_LIST_KEY)
    contracts: list[Contract] = json.loads(contract_data, cls=ContractDecoder) if contract_data else []
    logger.debug("Parsed %d contracts out of Valkey", len(contracts))

    contracts = [
        contract
        for contract in contracts
        if contract.status == ContractStatus.OUTSTANDING
        and (contract.assignee.id == int(corp_id) or contract.creator.id == int(corp_id))
        and contract.date_expired > datetime.now()
    ]

    logger.debug("%d contracts remaining after filtering", len(contracts))

    for contract in contracts:
        items: Any | None = valkey_client.get(CONTRACT_ITEMS_KEY.substitute(id=contract.contract_id))

        if items:
            logger.debug("Found items for contract %d", contract.contract_id)
            contract.items = aggregate_items(json.loads(items, cls=ItemDecoder), valkey_client)


        else:
            logger.warning("No items found for %d", contract.contract_id)

    return contracts

def aggregate_items(items: list[ContractItems], valkey_client: Valkey) -> list[ContractItems]:
    item_key: Callable[[ContractItems], int] = lambda item : item.item_type.id
    output = []

    requested_items = [item for item in items if item.status == ItemStatus.REQUESTED]
    offered_items = [item for item in items if item.status == ItemStatus.OFFERED]

    for key, elements in itertools.groupby(sorted(requested_items, key=item_key), key=item_key):
        count = sum(element.quantity for element in elements)
        redis_key = ITEM_NAME_KEY.substitute(id=key)
        item = NamedItem(id=key, name=valkey_client.get(redis_key))  # type: ignore
        output.append(ContractItems(item_type=item, quantity=count, status=ItemStatus.REQUESTED))
        
    for key, elements in itertools.groupby(sorted(offered_items, key=item_key), key=item_key):
        count = sum(element.quantity for element in elements)
        redis_key = ITEM_NAME_KEY.substitute(id=key)
        item = NamedItem(id=key, name=valkey_client.get(redis_key))  # type: ignore
        output.append(ContractItems(item_type=item, quantity=count, status=ItemStatus.OFFERED))

    return output


def create_contract_blueprint(corp_id: int, valkey_host: str, esi: ESI) -> Blueprint:
    valkey_client = Valkey(valkey_host, decode_responses=True)
    corp_id = CorpID(BaseID(corp_id))

    contract_endpoints = Blueprint("contracts", __name__)
    contract_endpoints.register_blueprint(create_station_blueprint(esi, valkey_client), url_prefix="/stations")

    def get_fuel_contracts() -> list[Contract]:
        MAGMATIC_GAS_TYPE_ID: int = 81143
        SUPERIONIC_ICE_TYPE_ID: int = 81144

        contracts = get_outstanding_contracts(corp_id, valkey_client)

        contracts = [
            contract
            for contract in contracts
            if contract.type == ContractType.ITEM_EXCHANGE
            and "skymule" not in contract.description.lower()
            and not any(item.item_type.id in [MAGMATIC_GAS_TYPE_ID, SUPERIONIC_ICE_TYPE_ID] for item in contract.items)
            # FIXME: This will filter out contracts that are trading fuel and it should not
            and not any(item.status == ItemStatus.OFFERED for item in contract.items)
        ]

        filtering(contracts)
        return contracts

    def filtering(contracts: list[Contract]) -> list[Contract]:
        filter_data = cast(set[str], valkey_client.smembers("filters"))
        filters = [ json.loads(x) for x in filter_data ]

        all_filters = filter_functions(valkey_client)        

        for contract in contracts:
            for filter in filters:
                filter_name: str = filter["name"]

                if not all_filters[filter_name](contract, filter.get("value", None)):
                    if filter["type"] == "Error":
                        contract.errors.append(filter_name)
                    else:
                        contract.warnings.append(filter_name)

        return contracts


    @contract_endpoints.route("/by-location")
    def aggregated() -> list[ByLocation]:
        contracts = get_fuel_contracts()

        item_key: Callable[[ContractItems], BaseID] = lambda item: item.item_type.id
        location_key: Callable[[Contract], BaseID] = lambda contract: contract.location.id

        fuelling_areas = cast(set[str], valkey_client.smembers(STATION_KEY))
        output = {
            int(location_id): ByLocation(structure=NamedItem(id=BaseID(int(location_id)), name=cast(str, valkey_client.get(ITEM_NAME_KEY.substitute(id=location_id))))) 
            for location_id in fuelling_areas }

        for location, contracts in itertools.groupby(sorted(contracts, key=location_key), key=location_key):
            if fuelling_areas and location not in output:
                print(f"Skipping {location} because it's not in {str(output)}")
                continue

            output_location = output.get(location)
            assert output_location is not None
                
            location_items = itertools.chain.from_iterable(contract.items for contract in contracts)
            location_items = [
                item for item in location_items if item.status == ItemStatus.REQUESTED
            ]  # Only look for requested items

            item_counts = []
            for key, elements in itertools.groupby(sorted(location_items, key=item_key), key=item_key):
                count = sum(element.quantity for element in elements)
                valkey_key = ITEM_NAME_KEY.substitute(id=key)
                item = NamedItem(id=BaseID(key), name=cast(str, valkey_client.get(valkey_key)))
                item_counts.append(ContractItems(item_type=item, quantity=count, status=ItemStatus.REQUESTED))

            print(f"Updating with {str(item_counts)}")
            output_location.items = item_counts

        assert None not in output.values()
        return [x for x in output.values()] #type: ignore


    @contract_endpoints.route("/all")
    def all_fuel_contracts() -> list[Contract]:
        return get_fuel_contracts()


    return contract_endpoints