import itertools
import json
import logging
from string import Template
from typing import cast
from collections.abc import Callable

from valkey import Valkey
from flask import Blueprint

from .dataclasses import *
from .filters import filter_functions
from data.esi import ESI
import database as db
import sqlalchemy as sa
import sqlalchemy.orm as so
from .typing import *
from .stations import create_station_blueprint, STATION_KEY

logger = logging.getLogger(__name__)
CONTRACT_LIST_KEY = "contracts"
CONTRACT_ITEMS_KEY = Template(f"{CONTRACT_LIST_KEY}:$id")
ITEM_NAME_KEY = Template("names:$id")

def get_outstanding_contracts(corp_id: CorpID, sql: sa.Engine) -> list[Contract]:
    with so.Session(sql) as session:
        new_contracts = list(session.scalars(sa.select(db.Contract).
                                            where(db.Contract.status == db.ContractStatus.OUTSTANDING).
                                            where(sa.or_(db.Contract.contracted_to == corp_id, db.Contract.contractor_id == corp_id))))
        
        return [Contract.from_database(x) for x in new_contracts]

def create_contract_blueprint(corp_id: int, valkey_host: str, esi: ESI, sql: sa.Engine) -> Blueprint:
    valkey_client = Valkey(valkey_host, decode_responses=True)
    corp_id = CorpID(BaseID(corp_id))

    contract_endpoints = Blueprint("contracts", __name__)
    contract_endpoints.register_blueprint(create_station_blueprint(esi, valkey_client), url_prefix="/stations")

    def get_fuel_contracts() -> list[Contract]:
        MAGMATIC_GAS_TYPE_ID: int = 81143
        SUPERIONIC_ICE_TYPE_ID: int = 81144

        contracts = get_outstanding_contracts(corp_id, sql)

        contracts = [
            contract
            for contract in contracts
            if contract.type in (ContractType.ITEM_EXCHANGE, ContractType.UNKNOWN)
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
        if not fuelling_areas:
            return []

        output = {
            int(location_id): ByLocation(structure=NamedItem(id=BaseID(int(location_id)), name=cast(str, valkey_client.get(ITEM_NAME_KEY.substitute(id=location_id))))) 
            for location_id in fuelling_areas }

        for location, contracts in itertools.groupby(sorted(contracts, key=location_key), key=location_key):
            if fuelling_areas and location not in output:
                logger.info(f"Skipping {location} because it's not in {str(output)}")
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
            output_location.contract_count = len(location_items)
            output_location.items = item_counts

        assert None not in output.values()
        return [x for x in output.values()] 


    @contract_endpoints.route("/all")
    def all_fuel_contracts() -> list[Contract]:
        return get_fuel_contracts()


    return contract_endpoints