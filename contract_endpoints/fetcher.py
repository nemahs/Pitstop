import itertools
import logging
import time
import traceback
from collections.abc import Callable, Iterable, Sequence
from datetime import datetime, timedelta
from typing import Final, cast

import requests
import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DatabaseError
from valkey import Valkey, ValkeyError

import database as db
from contract_endpoints.dataclasses import ContractItems, ItemStatus, NamedItem
from data.esi import ESI, ESIError, esi
from data.esi.esi import get_bulk_names, get_structure_names
from data.esi.typing import ContractID, CorporationID, EntityID, TypeID, make_character_id
from data.typing import AccessToken, RefreshToken

from .typing import *

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# region Constants
RATE_LIMIT_MULTIPLIER: Final[int] = 5  # Rate limit from ESI is multiplied to by this as a backoff
KEY_REFRESH_BUFFER: Final[int] = 100  # Seconds before expiry to refresh key
# endregion


def pull_contracts(esi: ESI, corp_id: CorporationID, valkey_host: str, sql: sa.Engine):
  valkey_client = Valkey(host=valkey_host, decode_responses=True)

  while True:
    try:
      if user := valkey_client.srandmember("characters"):
        assert isinstance(user, str)
        user_id = UserID(int(user))
        logger.info("Using user %d for contracts", user_id)

        logger.debug("Getting basic contract data for corp")
        contracts = get_basic_contract_data(esi, user_id, corp_id, valkey_client)
        # TODO: Handle the edge case where the list comes back empty

        logger.debug("Fetching names")

        with so.Session(sql) as session:
          hydrate_names(esi, contracts, user_id, valkey_client, session)
          hydrate_alliances(session, esi)

          session.commit()

          statement = insert(db.Contract).values(
            [
              dict(
                contract_id=contract.contract_id,
                contractor_id=contract.issuer_id,
                contracted_to=contract.assignee_id,
                location_id=contract.start_location_id,
                fueller_id=contract.acceptor_id,
                description=contract.title,
                status=contract.status,
                created_on=contract.date_issued,
                expires_on=contract.date_expired,
                filled_on=contract.date_completed,
              )
              for contract in contracts
              if (contract.assignee_id == corp_id or contract.issuer_id == corp_id)
              and contract.type == esi.ContractType.ITEM_EXCHANGE
              and contract.start_location_id is not None
            ]
          )

          statement = statement.on_conflict_do_update(
            index_elements=[db.Contract.contract_id],
            set_={
              db.Contract.status: statement.excluded["status"],
              db.Contract.filled_on: statement.excluded["filled_on"],
              db.Contract.fueller_id: statement.excluded["fueller_id"],
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
                [
                  db.ContractStatus.FINISHED,
                  db.ContractStatus.OUTSTANDING,
                  db.ContractStatus.IN_PROGRESS,
                ]
              )
            )
          )
          missing_items = [ContractID(x) for x in db_missing_items]

          logger.debug("%d Contracts to fetch items for: %s", len(missing_items), str(missing_items))
          for id in missing_items:
            access_token = get_key(esi, user_id, valkey_client)  # Reget key in case it expired

            try:
              logger.debug("Getting items for contract %d", id)
              items = esi.get_corp_contract_items(corp_id, id, access_token)
            except ESIError as err:
              match err.error_code:
                case requests.codes.too_many:
                  retry_after = int(err.headers.get("Retry-After", "10") if err.headers else 10) * RATE_LIMIT_MULTIPLIER
                  logger.warning("Rate limited, waiting %d seconds till we can continue", retry_after)
                  time.sleep(retry_after)
                case _:
                  logger.error("ESI ERROR ON CONTRACT %d, error code: %d", id, err.error_code)
              continue

            hydrate_items(items, session)

            if items:
              aggregated = aggregate_items(items)
              statement = (
                insert(db.ContractItem)
                .values(
                  [
                    dict(
                      type_id=x.item_type.id,
                      contract_id=id,
                      requested=x.status == ItemStatus.REQUESTED,
                      quantity=x.quantity,
                    )
                    for x in aggregated
                  ]
                )
                .on_conflict_do_nothing(
                  index_elements=[
                    db.ContractItem.type_id,
                    db.ContractItem.contract_id,
                    db.ContractItem.requested,
                  ]
                )
              )

              session.execute(statement)

            session.commit()
            time.sleep(1)  # We get 520'd if we poll too fast

          session.commit()

        # TODO: Properly wait for cache expiry to get data AFAP
        logger.info("Waiting 5 minutes")
        time.sleep(300)
    except (DatabaseError, ValkeyError) as err:
      logger.error("%s during contract pull: %s", type(err).__name__, err)
      time.sleep(30)
    # except err:
    #   logger.error("Ran into an unknown error, waiting, then trying again. Error: %s", err)
    #   traceback.print_exception(err)
    #   time.sleep(30)


def aggregate_items(items: list[ESIItem]) -> list[ContractItems]:
  output: list[ContractItems] = []
  item_key: Callable[[ESIItem], TypeID] = lambda item: item.type_id

  requested_items = [item for item in items if not item.is_included]
  offered_items = [item for item in items if item.is_included]

  def aggregate(subset: list[ESIItem], status: ItemStatus):
    for key, elements in itertools.groupby(sorted(subset, key=item_key), key=item_key):
      count = sum(element.quantity for element in elements)
      output.append(
        ContractItems(
          item_type=NamedItem(id=key, name=""),
          quantity=count,
          status=status,
        )
      )

  aggregate(requested_items, ItemStatus.REQUESTED)
  aggregate(offered_items, ItemStatus.OFFERED)

  return output


def get_basic_contract_data(
  esi: ESI, user_id: UserID, corp_id: CorporationID, valkey_client: Valkey
) -> list[ESIContract]:
  access_token = get_key(esi, user_id, valkey_client)
  return esi.get_corp_contracts(corp_id, access_token)


# region Database Hydration


def hydrate_alliances(session: so.Session, esi: ESI):
  ALLIANCE_EXPIRATION: Final[timedelta] = timedelta(days=7)
  get_alliances_to_update = sa.select(db.ContractEntity.id).where(
    db.ContractEntity.type == db.EntityType.CHARACTER).where(
      (db.ContractEntity.alliance == None) |
      (db.ContractEntity.updated_at == None) |
       (datetime.now() - db.ContractEntity.updated_at > ALLIANCE_EXPIRATION)
    )

  missing_alliances = session.scalars(get_alliances_to_update)

  logger.debug("Working on missing character alliances")
  missing_alliances = [make_character_id(x) for x in missing_alliances]
  logger.debug("%d alliances to fetch", len(missing_alliances))
  alliance_info = esi.get_alliances_for_characters(missing_alliances)
  for character_id, alliance in alliance_info.items():
    if character := session.get(db.ContractEntity, character_id):
      if alliance and not session.get(db.Alliance, alliance):
        name = get_bulk_names([alliance])[alliance]
        session.add(db.Alliance(id=alliance, name=name.name))
        logger.debug("Updating alliance")
      character.alliance_id = alliance
      character.updated_at = datetime.now()

  session.commit()


def hydrate_names(
  esi: ESI,
  contracts: Sequence[ESIContract],
  user_id: UserID,
  valkey_client: Valkey,
  session: so.Session,
):
  hydrate_entities(contracts, "issuer_id", session)
  hydrate_entities(contracts, "assignee_id", session)
  hydrate_entities(contracts, "acceptor_id", session)

  access_token = get_key(esi, user_id, valkey_client)
  hydrate_structures(contracts, "start_location_id", access_token, session)

  session.commit()


def hydrate_structures(
  contracts: Sequence[ESIContract],
  attr: str,
  access_token: AccessToken,
  session: so.Session,
):
  contract_ids: set[ContractID] = {contract.__getattribute__(attr) for contract in contracts}
  result = session.scalars(sa.select(db.Structure.id).filter(db.Structure.id.in_(contract_ids)))
  known_ids = set(result)
  unknown_ids = contract_ids.difference(known_ids)

  unknown_ids = list(unknown_ids)

  logger.debug(
    "%d known %s ids, %d unknown %s ids",
    len(known_ids),
    attr,
    len(unknown_ids),
    attr,
  )

  if unknown_ids:
    new_names = get_structure_names(unknown_ids, access_token)
    for id, name in new_names.items():
      new_item = db.Structure(id=id, name=name)
      session.add(new_item)
      logger.debug("Set name for %d", id)

    session.commit()


def hydrate_entities(contracts: Sequence[ESIContract], attr: str, session: so.Session):
  contract_ids: set[EntityID] = {contract.__getattribute__(attr) for contract in contracts}
  result = session.scalars(sa.select(db.ContractEntity.id).filter(db.ContractEntity.id.in_(contract_ids)))
  known_ids = {EntityID(x) for x in result}
  unknown_ids = contract_ids - known_ids

  unknown_ids: Iterable[EntityID] = list(unknown_ids)

  logger.debug(
    "%d known %s ids, %d unknown %s ids",
    len(known_ids),
    attr,
    len(unknown_ids),
    attr,
  )

  if unknown_ids:
    new_names = get_bulk_names(unknown_ids)
    for id, name in new_names.items():
      new_item = db.ContractEntity(id=id, name=name.name, type=convert_category(name.category))
      session.add(new_item)
      logger.debug("Set name for %d", id)

  session.commit()


def hydrate_items(items: Sequence[ESIItem], session: so.Session):
  type_ids = {contract.type_id for contract in items}
  result = session.scalars(sa.select(db.ItemType.id).filter(db.ItemType.id.in_(type_ids)))
  known_ids = set(result)
  unknown_ids = type_ids - known_ids

  unknown_ids: Iterable[TypeID] = list(unknown_ids)

  logger.debug(
    "%d known type ids, %d unknown type ids",
    len(known_ids),
    len(unknown_ids),
  )

  if unknown_ids:
    new_names = get_bulk_names(unknown_ids)
    for id, name in new_names.items():
      new_item = db.ItemType(id=id, name=name.name)
      session.add(new_item)
      logger.debug("Set name for %d", id)

    session.commit()


# endregion


def convert_category(category: esi.ESIEntity) -> db.EntityType:
  match category:
    case esi.ESIEntity.CHARACTER:
      return db.EntityType.CHARACTER
    case esi.ESIEntity.CORPORATION:
      return db.EntityType.CORPORATION
    case esi.ESIEntity.ALLIANCE:
      return db.EntityType.ALLIANCE
    case _:
      return db.EntityType.UNKNOWN


def get_key(esi: ESI, user_id: UserID, valkey_client: Valkey) -> AccessToken:
  """Get the access token for a user, refreshing it if necessary.

  :param esi: ESI object to user for refreshing token if needed
  :param user_id: UserID of the user to get the token for

  :return: ESI AccessToken for user
  """
  if (
    valkey_client.exists(f"{user_id}:access_token")
    and (remaining_ttl := int(valkey_client.ttl(f"{user_id}:access_token"))) > KEY_REFRESH_BUFFER  # type: ignore
  ):
    data = valkey_client.get(f"{user_id}:access_token")
    assert isinstance(data, str), f"Data was of type {type(data)}"
    logger.debug("%d seconds left in access token", remaining_ttl)
    return AccessToken(data)

  refresh_token_data = cast(str, valkey_client.get(f"{user_id}:refresh_token"))
  refresh_token = RefreshToken(refresh_token_data)

  token_data = esi.refresh_tokens(refresh_token)
  valkey_client.set(f"{user_id}:access_token", token_data.access_token, ex=token_data.expiry)

  return token_data.access_token
