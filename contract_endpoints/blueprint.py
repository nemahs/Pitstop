import itertools
import json
import logging
from typing import Final, cast

import sqlalchemy as sa
import sqlalchemy.orm as so
from flask import Blueprint
from valkey import Valkey

import database as db
from data.esi import ESI

from .dataclasses import ByLocation, Contract, ContractItems, ContractType, ItemStatus, NamedItem
from .filters import filter_functions
from .stations import STATION_KEY, create_station_blueprint
from .typing import BaseID, CorpID

logger = logging.getLogger(__name__)


type Contracts = list[Contract]


def get_outstanding_contracts(corp_id: CorpID, sql: sa.Engine) -> Contracts:
  with so.Session(sql) as session:
    new_contracts = list(
      session.scalars(
        sa.select(db.Contract)
        .where(db.Contract.status == db.ContractStatus.OUTSTANDING)
        .where(sa.or_(db.Contract.contracted_to == corp_id, db.Contract.contractor_id == corp_id))
      )
    )

    return [Contract.from_database(x) for x in new_contracts]


def create_contract_blueprint(corp_id: int, valkey_host: str, esi: ESI, sql: sa.Engine) -> Blueprint:
  valkey_client = Valkey(valkey_host, decode_responses=True)
  corp_id = CorpID(BaseID(corp_id))

  contract_endpoints = Blueprint('contracts', __name__)
  contract_endpoints.register_blueprint(create_station_blueprint(esi, valkey_client, sql), url_prefix='/stations')

  def get_fuel_contracts() -> Contracts:
    MAGMATIC_GAS_TYPE_ID: Final = 81143
    SUPERIONIC_ICE_TYPE_ID: Final = 81144

    contracts = get_outstanding_contracts(corp_id, sql)

    contracts = [
      contract
      for contract in contracts
      if contract.type in (ContractType.ITEM_EXCHANGE, ContractType.UNKNOWN)
      and 'skymule' not in contract.description.lower()
      and not any(item.item_type.id in [MAGMATIC_GAS_TYPE_ID, SUPERIONIC_ICE_TYPE_ID] for item in contract.items)
      # FIXME: This will filter out contracts that are trading fuel and it should not
      and not any(item.status == ItemStatus.OFFERED for item in contract.items)
    ]

    filtering(contracts)
    return contracts

  def filtering(contracts: Contracts) -> Contracts:
    # TODO: Move to database
    filter_data = cast(set[str], valkey_client.smembers('filters'))
    filters = [json.loads(x) for x in filter_data]

    all_filters = filter_functions(valkey_client)

    for contract in contracts:
      for filter in filters:
        filter_name: str = filter['name']

        if not all_filters[filter_name](contract, filter.get('value', None)):
          if filter['type'] == 'Error':
            contract.errors.append(filter_name)
          else:
            contract.warnings.append(filter_name)

    return contracts

  @contract_endpoints.route('/by-location')
  def aggregated() -> list[ByLocation]:
    contracts = get_fuel_contracts()

    def get_item_key(item: ContractItems) -> BaseID:
      return item.item_type.id

    def get_location_key(contract: Contract) -> BaseID:
      return contract.location.id if contract.location else BaseID(0)

    fuelling_areas = cast(set[str], valkey_client.smembers(STATION_KEY))
    if not fuelling_areas:
      return []

    with so.Session(sql) as session:
      output = session.execute(sa.select(db.Structure.id, db.Structure.name).where(db.Structure.id.in_(fuelling_areas)))
      output = {id: ByLocation(structure=NamedItem(id=BaseID(id), name=name)) for id, name in output}

    for location, contracts in itertools.groupby(sorted(contracts, key=get_location_key), key=get_location_key):
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
      for key, elements in itertools.groupby(sorted(location_items, key=get_item_key), key=get_item_key):
        with so.Session(sql) as session:
          count = sum(element.quantity for element in elements)
          contract_item: db.ItemType | None = session.get(db.ItemType, key)
          item = NamedItem(id=BaseID(contract_item.id), name=contract_item.name) if contract_item else None
          if item:
            item_counts.append(ContractItems(item_type=item, quantity=count, status=ItemStatus.REQUESTED))

      print(f'Updating with {str(item_counts)}')
      output_location.contract_count = len(location_items)
      output_location.items = item_counts

    assert None not in output.values()
    return [x for x in output.values()]

  @contract_endpoints.route('/all')
  def all_fuel_contracts() -> Contracts:
    return get_fuel_contracts()

  return contract_endpoints
