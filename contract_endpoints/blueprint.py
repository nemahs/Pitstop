import itertools
import json
import logging
from datetime import datetime
from typing import Any, List, Callable, cast

import valkey
from flask import Blueprint

from .dataclasses import *
from .typing import *


class ContractBlueprint(Blueprint):
    def __init__(self, name: str, import_name: str, corp_id: CorpID | None = None):
        super().__init__(name, import_name)
        self.corp_id = corp_id

    def create_valkey_client(self, host: str) -> None:
        self.valkey_client = valkey.Valkey(host=host)


contract_endpoints = ContractBlueprint("contracts", __name__)
logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)


# TODO: Make filters configurable
def get_outstanding_contracts(corp_id: CorpID) -> list[Contract]:
    assert contract_endpoints.valkey_client is not None
    contract_data: Any | None = contract_endpoints.valkey_client.get("contracts")
    contracts: List[Contract] = json.loads(contract_data, cls=ContractDecoder) if contract_data else []
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
        items: Any | None = contract_endpoints.valkey_client.get(f"contracts:{contract.contract_id}")

        if items:
            logger.debug(f"Found items for contract {contract.contract_id}")
            contract.items = aggregate_items(json.loads(items, cls=ItemDecoder))


        else:
            logger.warning(f"No items found for {contract.contract_id}")

    return contracts


def aggregate_items(items: list[ContractItems]) -> list[ContractItems]:
    item_key: Callable[[ContractItems], int] = lambda item : item.item_type.id
    output = []

    requested_items = [item for item in items if item.status == ItemStatus.REQUESTED]
    offered_items = [item for item in items if item.status == ItemStatus.OFFERED]

    for key, elements in itertools.groupby(sorted(requested_items, key=item_key), key=item_key):
        count = sum(element.quantity for element in elements)
        item = NamedItem(id=BaseID(key), name=bytes(contract_endpoints.valkey_client.get(f"names:{key}")).decode())  # type: ignore
        output.append(ContractItems(item_type=item, quantity=count, status=ItemStatus.REQUESTED))
        
    for key, elements in itertools.groupby(sorted(offered_items, key=item_key), key=item_key):
        count = sum(element.quantity for element in elements)
        item = NamedItem(id=BaseID(key), name=bytes(contract_endpoints.valkey_client.get(f"names:{key}")).decode())  # type: ignore
        output.append(ContractItems(item_type=item, quantity=count, status=ItemStatus.OFFERED))

    return output



def get_fuel_contracts() -> list[Contract]:
    MAGMATIC_GAS_TYPE_ID: int = 81143
    SUPERIONIC_ICE_TYPE_ID: int = 81144

    assert contract_endpoints.corp_id is not None
    contracts = get_outstanding_contracts(contract_endpoints.corp_id)

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

type FilterFunction = Callable[[Contract, Any | None], bool]

def fuelInRange(contract: Contract, max: int | None) -> bool:
    ISOTOPE_IDS = [16274, 17887, 17888, 17889]
    fuel_items = [item for item in contract.items if item.item_type.id in ISOTOPE_IDS]

    if not max:
        return True

    for fuel in fuel_items:
        if fuel.quantity >= max:
            return False
        
    return True

def isInfoPopulated(contract: Contract, _: Any | None) -> bool:
    return len(contract.description) > 0

def isFuelRounded(contract: Contract, roundingValue: int | None) -> bool:
    ISOTOPE_IDS = [16274, 17887, 17888, 17889]

    if not roundingValue:
        return True

    fuel_items = [item for item in contract.items if item.item_type.id in ISOTOPE_IDS]

    for fuel in fuel_items:
        if fuel.quantity % roundingValue != 0:
            return False
        
    return True

def isStrontHigh(contract: Contract, max: int | None) -> bool:
    STRONT_ID = 16275

    if not max:
        return True

    total_stront: int = sum([item.quantity for item in contract.items if item.item_type.id == STRONT_ID])

    return total_stront < max

def inAllowedAlliances(contract: Contract, alliance_ids: list[str] | None) -> bool:
    if not alliance_ids:
        return True

    print(f"Checking {contract.alliance} against {str(alliance_ids)}")
    return str(contract.alliance) in alliance_ids or contract.alliance is None

filter_functions: dict[str, FilterFunction]  = {
    "infoPopulated": isInfoPopulated,
    "fuelHigh": fuelInRange,
    "fuelRounding": isFuelRounded,
    "strontHigh": isStrontHigh,
    "allianceCheck": inAllowedAlliances
}


def filtering(contracts: list[Contract]) -> list[Contract]:

    filter_data = cast(set[bytes], contract_endpoints.valkey_client.smembers("filters"))

    filters = [ json.loads(x) for x in filter_data ]

    for contract in contracts:
        for filter in filters:
            if not filter_functions[filter["name"]](contract, filter.get("value", None)):
                if filter["type"] == "Error":
                    contract.errors.append(filter["name"])
                else:
                    contract.warnings.append(filter["name"])

    return contracts


@contract_endpoints.route("/by-location")
def aggregated() -> list[ByLocation]:

    assert contract_endpoints.corp_id is not None
    contracts = get_fuel_contracts()
    output = []

    item_key = lambda item: item.item_type.id
    location_key = lambda contract: contract.location.id

    for location, contracts in itertools.groupby(sorted(contracts, key=location_key), key=location_key):
        location_name: str = bytes(contract_endpoints.valkey_client.get(f"names:{location}")).decode()  # type: ignore
        new_location = ByLocation(structure=NamedItem(id=BaseID(location), name=location_name))

        location_items = itertools.chain.from_iterable(contract.items for contract in contracts)
        location_items = [
            item for item in location_items if item.status == ItemStatus.REQUESTED
        ]  # Only look for requested items

        item_counts = []
        for key, elements in itertools.groupby(sorted(location_items, key=item_key), key=item_key):
            count = sum(element.quantity for element in elements)
            item = NamedItem(id=BaseID(key), name=bytes(contract_endpoints.valkey_client.get(f"names:{key}")).decode())  # type: ignore
            item_counts.append(ContractItems(item_type=item, quantity=count, status=ItemStatus.REQUESTED))

        new_location.items = item_counts

        output.append(new_location)

    return output


@contract_endpoints.route("/all")
def all_fuel_contracts() -> list[Contract]:
    return get_fuel_contracts()
