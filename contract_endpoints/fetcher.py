import itertools
import logging
import time
from collections.abc import Iterable, Sequence
from typing import cast

import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DatabaseError
from valkey import Valkey, ValkeyError

import database as db
from contract_endpoints.dataclasses import ContractItems, ItemStatus, NamedItem
from data.data_source import OauthProvider
from data.esi import ESI, ESIError
from data.esi.auth import ESIAuth  # TODO: DEAR GOD FIX
from data.esi.esi import ESIEntity, parseRFC7231Date
from data.typing import AccessToken, RefreshToken

from .typing import BaseID, ContractID, CorpID, ESIContract, ESIItem, UserID

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARN)


def pull_contracts(esi: ESI, auth: OauthProvider, corp_id: CorpID, valkey_host: str, sql: sa.Engine):
  valkey_client = Valkey(host=valkey_host, decode_responses=True)

  while True:
    try:
      if user := valkey_client.srandmember('characters'):
        assert isinstance(user, str)
        user_id = UserID(BaseID(int(user)))
        logger.info('Using user %d for contracts', user_id)

        logger.debug('Getting basic contract data for corp')
        contracts = get_basic_contract_data(esi, auth, user_id, corp_id, valkey_client)

        logger.debug('Fetching names')

        with so.Session(sql) as session:
          hydrate_names(esi, auth, contracts, user_id, valkey_client, session)
          hydrate_alliances(session, esi)

          session.commit()

          statement = insert(db.Contract).values(
            [
              dict(
                contract_id=x['contract_id'],
                contractor_id=x['issuer_id'],
                contracted_to=x['assignee_id'],
                location_id=x['start_location_id'],
                fueller_id=x['acceptor_id'],
                description=x.get('title', None),
                status=x['status'],
                created_on=parseRFC7231Date(x['date_issued']),
                expires_on=parseRFC7231Date(x['date_expired']),
                filled_on=parseRFC7231Date(x['date_completed']) if 'date_completed' in x else None,
              )
              for x in contracts
              if (x['assignee_id'] == corp_id or x['issuer_id'] == corp_id)
              and x['type'] == esi.ContractType.ITEM_EXCHANGE
              and 'start_location_id' in x
            ]
          )

          statement = statement.on_conflict_do_update(
            index_elements=[db.Contract.contract_id],
            set_={
              db.Contract.status: statement.excluded['status'],
              db.Contract.filled_on: statement.excluded['filled_on'],
              db.Contract.fueller_id: statement.excluded['fueller_id'],
            },
          )

          session.execute(statement)

          statement = sa.select(db.ContractItem.contract_id).where(
            db.ContractItem.contract_id == db.Contract.contract_id
          )

          db_missing_items = session.scalars(
            sa.select(db.Contract.contract_id)
            .where(~sa.exists(statement))
            .where(
              db.Contract.status.in_(
                [db.ContractStatus.FINISHED, db.ContractStatus.OUTSTANDING, db.ContractStatus.IN_PROGRESS]
              )
            )
          )
          missing_items = [ContractID(BaseID(x)) for x in db_missing_items]

          logger.debug('Contracts to fetch items for: %s', str(missing_items))
          for id in missing_items:
            access_token = get_key(auth, user_id, valkey_client)  # Reget key in case it expired

            try:
              logger.debug('Getting items for contract %d', id)
              items = esi.get_corp_contract_items(corp_id, id, access_token)
            except ESIError:
              logger.error('ESI ERROR ON CONTRACT %d', id)
              continue

            hydrate_items(items, esi, session)

            if items:
              aggregated = aggregate_items(items)
              statement = (
                insert(db.ContractItem)
                .values(
                  [
                    dict(
                      type_id=x.item_type.id,
                      contract_id=id,
                      requested=True if x.status == ItemStatus.REQUESTED else False,
                      quantity=x.quantity,
                    )
                    for x in aggregated
                  ]
                )
                .on_conflict_do_nothing(
                  index_elements=[db.ContractItem.type_id, db.ContractItem.contract_id, db.ContractItem.requested]
                )
              )

              session.execute(statement)

            session.commit()
            time.sleep(0.2)  # We get 520'd if we poll too fast

          session.commit()

        logger.info('Waiting 5 minutes')  # TODO: Properly wait for cache expiry to get data AFAP
        time.sleep(300)
    except DatabaseError as e:
      logger.error('Ran into a database issue, waiting then trying again. Issue: %s', e)
      time.sleep(30)
    except ValkeyError as e:
      logger.error('Ran into a valkey issue, waiting to try again, message: %s', e)
      time.sleep(30)
    except Exception as e:
      logger.error('Ran into an unknown error, waiting, then trying again. Error: %s', e)
      time.sleep(30)


def aggregate_items(items: list[ESIItem]) -> list[ContractItems]:
  output: list[ContractItems] = []

  def get_item_key(item: ESIItem) -> BaseID:
    return BaseID(item['type_id'])

  requested_items = [item for item in items if not item['is_included']]
  offered_items = [item for item in items if item['is_included']]

  def aggregate(subset: list[ESIItem], status: ItemStatus):
    for key, elements in itertools.groupby(sorted(subset, key=get_item_key), key=get_item_key):
      count = sum(element['quantity'] for element in elements)
      output.append(ContractItems(item_type=NamedItem(id=key, name=''), quantity=count, status=status))

  aggregate(requested_items, ItemStatus.REQUESTED)
  aggregate(offered_items, ItemStatus.OFFERED)

  return output


def get_basic_contract_data(esi: ESI, auth: OauthProvider, user_id: UserID, corp_id: CorpID, valkey_client: Valkey) -> list[ESIContract]:
  access_token = get_key(auth, user_id, valkey_client)
  contracts = esi.get_corp_contracts(corp_id, access_token)
  return contracts


# region Database Hydration


def hydrate_alliances(session: so.Session, esi: ESI):
  missing_alliances = session.scalars(
    sa.select(db.ContractEntity.id)
    .where(db.ContractEntity.alliance == None)  # noqa: E711 DB query does not support 'is' or 'is not'
    .where(db.ContractEntity.type == db.EntityType.CHARACTER)
  )

  logger.debug('Working on missing character alliances')
  alliance_info = esi.get_alliances_for_characters(list(missing_alliances))
  for character_id, alliance in alliance_info.items():
    if character := session.get(db.ContractEntity, character_id):
      if alliance and not session.get(db.Alliance, alliance):
        name = esi.get_bulk_names([alliance])[alliance]
        session.add(db.Alliance(id=alliance, name=name.name))
      character.alliance_id = alliance

  session.commit()


def hydrate_names(
  esi: ESI, auth: OauthProvider, contracts: Sequence[ESIContract], user_id: UserID, valkey_client: Valkey, session: so.Session
):
  hydrate_entities(contracts, 'issuer_id', session=session, esi=esi)
  hydrate_entities(contracts, 'assignee_id', session=session, esi=esi)
  hydrate_entities(contracts, 'acceptor_id', session=session, esi=esi)

  access_token = get_key(auth, user_id, valkey_client)
  hydrate_structures(contracts, 'start_location_id', access_token, esi=esi, session=session)

  session.commit()


def hydrate_structures(
  contracts: Sequence[ESIContract], attr: str, access_token: AccessToken, *, esi: ESI, session: so.Session
):
  contract_ids = {contract[attr] for contract in contracts}
  result = session.scalars(sa.select(db.Structure.id).filter(db.Structure.id.in_(contract_ids)))
  known_ids = {BaseID(x) for x in result}
  unknown_ids = contract_ids - known_ids

  unknown_ids: Iterable[BaseID] = list(unknown_ids)

  logger.debug('%d known %s ids, %d unknown %s ids', len(known_ids), attr, len(unknown_ids), attr)

  if unknown_ids:
    new_names = esi.get_structure_names(unknown_ids, access_token)
    for id, name in new_names.items():
      new_item = db.Structure(id=id, name=name)
      session.add(new_item)
      logger.debug('Set name for %d', id)

    session.commit()


def hydrate_entities(contracts: Sequence[ESIContract], attr: str, *, esi: ESI, session: so.Session):
  contract_ids = {contract[attr] for contract in contracts}
  result = session.scalars(sa.select(db.ContractEntity.id).filter(db.ContractEntity.id.in_(contract_ids)))
  known_ids = {BaseID(x) for x in result}
  unknown_ids = contract_ids - known_ids

  unknown_ids: Iterable[BaseID] = list(unknown_ids)

  logger.debug('%d known %s ids, %d unknown %s ids', len(known_ids), attr, len(unknown_ids), attr)

  if unknown_ids:
    new_names = esi.get_bulk_names(unknown_ids)
    for id, name in new_names.items():
      new_item = db.ContractEntity(id=id, name=name.name, type=convert_category(name.category))
      session.add(new_item)
      logger.debug('Set name for %d', id)

    session.commit()


def hydrate_items(items: Sequence[ESIItem], esi: ESI, session: so.Session):
  type_ids = {BaseID(contract['type_id']) for contract in items}
  result = session.scalars(sa.select(db.ItemType.id).filter(db.ItemType.id.in_(type_ids)))
  known_ids = {BaseID(x) for x in result}
  unknown_ids = type_ids - known_ids

  unknown_ids: Iterable[BaseID] = list(unknown_ids)

  logger.debug('%d known %s ids, %d unknown %s ids', len(known_ids), 'type_id', len(unknown_ids), 'type_id')

  if unknown_ids:
    new_names = esi.get_bulk_names(unknown_ids)
    for id, name in new_names.items():
      new_item = db.ItemType(id=id, name=name.name)
      session.add(new_item)
      logger.debug('Set name for %d', id)

    session.commit()


# endregion


def convert_category(category: ESIEntity) -> db.EntityType:
  if category == ESIEntity.CHARACTER:
    return db.EntityType.CHARACTER
  elif category == ESIEntity.CORPORATION:
    return db.EntityType.CORPORATION
  elif category == ESIEntity.ALLIANCE:
    return db.EntityType.ALLIANCE
  else:
    return db.EntityType.UNKNOWN


def get_key(auth: OauthProvider, user_id: UserID, valkey_client: Valkey) -> AccessToken:
  """Get the access token for a user, refreshing it if necessary.

  :param esi: ESI object to user for refreshing token if needed
  :param user_id: UserID of the user to get the token for

  :return: ESI AccessToken for user
  """
  if (
    valkey_client.exists(f'{user_id}:access_token')
    and (remaining_ttl := int(valkey_client.ttl(f'{user_id}:access_token'))) > 100  # type: ignore
  ):
    data = valkey_client.get(f'{user_id}:access_token')
    assert isinstance(data, str), f'Data was of type {type(data)}'
    logger.debug('%d seconds left in access token', remaining_ttl)
    return AccessToken(data)

  refresh_token_data = cast(str, valkey_client.get(f'{user_id}:refresh_token'))
  refresh_token = RefreshToken(refresh_token_data)

  token_data = auth.refresh_tokens(refresh_token)
  valkey_client.set(f'{user_id}:access_token', token_data.access_token, ex=token_data.expiry)

  return token_data.access_token
