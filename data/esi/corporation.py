import logging
from datetime import datetime
from enum import Enum
from typing import Annotated

import requests
from pydantic import BaseModel, Field, NonNegativeFloat, PositiveFloat, PositiveInt, TypeAdapter

from ..typing import AccessToken
from .typing import ContractID, CorporationID, EntityID, StructureID, TypeID
from .utils import ESI_BASE_URL, ESIError, auth_headers

logger = logging.getLogger(__name__)


class ContractStatus(str, Enum):
  OUTSTANDING = "outstanding"
  IN_PROGRESS = "in_progress"
  FINISHED_ISSUER = "finished_issuer"
  FINISHED_CONTRACTOR = "finished_contractor"
  FINISHED = "finished"
  CANCELLED = "cancelled"
  REJECTED = "rejected"
  FAILED = "failed"
  DELETED = "deleted"
  REVERSED = "reversed"


class ContractType(str, Enum):
  UNKNOWN = "unknown"
  ITEM_EXCHANGE = "item_exchange"
  AUCTION = "auction"
  COURIER = "courier"
  LOAN = "loan"


class ContractAvailability(str, Enum):
  PUBLIC = "public"
  CORPORATION = "corporation"
  ALLIANCE = "alliance"
  PERSONAL = "personal"


class ESIContract(BaseModel):
  acceptor_id: EntityID
  assignee_id: EntityID
  availability: ContractAvailability
  buyout: NonNegativeFloat | None = None
  collateral: NonNegativeFloat | None = None
  contract_id: ContractID
  date_accepted: datetime | None = None
  date_completed: datetime | None = None
  date_expired: datetime
  date_issued: datetime
  days_to_complete: int | None = None
  end_location_id: StructureID | None = None
  for_corporation: bool
  issuer_corporation_id: CorporationID
  issuer_id: EntityID
  price: NonNegativeFloat | None = None
  reward: NonNegativeFloat | None = None
  start_location_id: StructureID | None = None
  status: ContractStatus
  title: str | None = None
  type: ContractType
  volume: NonNegativeFloat | None = None


class ESIItem(BaseModel):
  is_included: bool
  is_singleton: bool
  quantity: PositiveInt
  raw_quantity: int | None = None
  record_id: int
  type_id: TypeID


def get_corp_contracts(_, corp_id: CorporationID, access_token: AccessToken) -> list[ESIContract]:
  ContractList = TypeAdapter(list[ESIContract])
  response = requests.get(
    f"{ESI_BASE_URL}/corporations/{corp_id}/contracts/",
    headers=auth_headers(access_token),
  )

  if response.status_code != requests.codes.ok:
    logger.error(f"Error occurred while fetching contracts, response code {response.status_code}, text {response.text}")
    return []

  contracts: list[ESIContract] = ContractList.validate_json(response.text)

  remaining_pages = response.headers.get("x-pages", 0)
  logger.info("%d pages of contracts to fetch", int(remaining_pages))

  if remaining_pages:
    for page in range(2, int(remaining_pages) + 1):
      response = requests.get(
        f"{ESI_BASE_URL}/corporations/{corp_id}/contracts/?page={page}",
        headers=auth_headers(access_token),
      )

      if response.status_code != requests.codes.ok:
        continue  # TODO: Retry

      contracts.extend(ContractList.validate_python(response.json()))


  logger.info("Fetched %d contracts", len(contracts))
  return contracts


def get_corp_contract_items(_, corp_id: CorporationID, contract_id: ContractID, access_token: AccessToken) -> list[ESIItem]:
  ItemList = TypeAdapter(list[ESIItem])
  response = requests.get(
    f"{ESI_BASE_URL}/corporations/{corp_id}/contracts/{contract_id}/items/",
    headers=auth_headers(access_token),
  )

  if response.status_code != requests.codes.ok:
    logger.error(f"Error occurred while fetching items for {contract_id}, response code {response.status_code}")
    raise ESIError("Failed to get items for contract", error_code=response.status_code, headers=response.headers)

  logger.info(f"Fetched items for contract {contract_id}")
  return ItemList.validate_json(response.text)


def open_corp_contract(contract_id: CorporationID, access_token: AccessToken):
  response = requests.post(
    f"{ESI_BASE_URL}/ui/openwindow/contract?contract_id={contract_id}", headers=auth_headers(access_token)
  )

  if response.status_code != requests.status_codes.codes.OK:
    logger.error(f"Error occurred trying to open contract window, code: {response.status_code}, text: {response.text}")
