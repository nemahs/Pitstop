import itertools
import logging
from collections.abc import Callable
from string import Template
from typing import Final, Literal, cast

import sqlalchemy as sa
import sqlalchemy.orm as so
from flask import Blueprint
from pydantic import BaseModel
from valkey import Valkey

import database as db
from data.esi import ESI
from data.esi.typing import CorporationID

from .dataclasses import *
from .filters import FilterFunctions, filter_functions
from .stations import STATION_KEY, create_station_blueprint
from .typing import *

logger = logging.getLogger(__name__)
CONTRACT_LIST_KEY = "contracts"
CONTRACT_ITEMS_KEY = Template(f"{CONTRACT_LIST_KEY}:$id")
ITEM_NAME_KEY = Template("names:$id")


def get_outstanding_contracts(corp_id: CorporationID, sql: sa.Engine) -> list[Contract]:
  with so.Session(sql) as session:
    new_contracts = list(
      session.scalars(
        sa.select(db.Contract)
        .where(db.Contract.status == db.ContractStatus.OUTSTANDING)
        .where(sa.or_(db.Contract.contracted_to == corp_id, db.Contract.contractor_id == corp_id))
        .where(db.Contract.expires_on > datetime.now())
      )
    )

    return [Contract.from_database(x) for x in new_contracts]


class ValkeyFilter(BaseModel):
  name: FilterFunctions
  type: Literal["Error", "Warning", "Info"]
  value: Any | None = None


def create_contract_blueprint(corp_id: CorporationID, valkey_host: str, esi: ESI, sql: sa.Engine) -> Blueprint:
  valkey_client = Valkey(valkey_host, decode_responses=True)

  contract_endpoints = Blueprint("contracts", __name__)
  contract_endpoints.register_blueprint(create_station_blueprint(esi, valkey_client, sql), url_prefix="/stations")

  def get_fuel_contracts() -> list[Contract]:
    MAGMATIC_GAS_TYPE_ID: Final[int] = 81143
    SUPERIONIC_ICE_TYPE_ID: Final[int] = 81144

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
    filters = [ValkeyFilter.model_validate_json(x) for x in filter_data]

    all_filters = filter_functions(valkey_client)

    for contract in contracts:
      for filter in filters:
        filter_name: FilterFunctions = filter.name

        if not all_filters[filter_name](contract, filter.value):
          if filter.type == "Error":
            contract.errors.append(filter_name)
          else:
            contract.warnings.append(filter_name)

    return contracts

  @contract_endpoints.route("/by-location")
  def aggregated() -> list[ByLocation]:
    contracts = get_fuel_contracts()

    item_key: Callable[[ContractItems], TypeID] = lambda item: item.item_type.id
    location_key: Callable[[Contract], StructureID] = lambda contract: contract.location.id

    fuelling_areas = cast(set[str], valkey_client.smembers(STATION_KEY))
    if not fuelling_areas:
      return []

    with so.Session(sql) as session:
      output = session.execute(sa.select(db.Structure.id, db.Structure.name).where(db.Structure.id.in_(map(int, fuelling_areas))))
      output = {id: ByLocation(structure=NamedItem(id=id, name=name)) for id, name in output}

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
        item = NamedItem(id=key, name=cast(str, valkey_client.get(valkey_key)))
        item_counts.append(ContractItems(item_type=item, quantity=count, status=ItemStatus.REQUESTED))

      output_location.contract_count = len(location_items)
      output_location.items = item_counts

    assert None not in output.values()
    return list(output.values())

  @contract_endpoints.route("/all")
  def all_fuel_contracts() -> list[Contract]:
    return get_fuel_contracts()

  return contract_endpoints
