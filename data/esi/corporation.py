import logging
from enum import Enum
from typing import Any, Required, TypedDict

import requests

from data.esi.utils import corp_auth

logger = logging.getLogger(__name__)


class ContractStatus(str, Enum):
  OUTSTANDING = 'outstanding'
  IN_PROGRESS = 'in_progress'
  FINISHED_ISSUER = 'finished_issuer'
  FINISHED_CONTRACTOR = 'finished_contractor'
  FINISHED = 'finished'
  CANCELLED = 'cancelled'
  REJECTED = 'rejected'
  FAILED = 'failed'
  DELETED = 'deleted'
  REVERSED = 'reversed'


class ContractType(str, Enum):
  UNKNOWN = 'unknown'
  ITEM_EXCHANGE = 'item_exchange'
  AUCTION = 'auction'
  COURIER = 'courier'
  LOAN = 'loan'


class ESIContract(TypedDict, total=False):
  acceptor_id: Required[int]
  assignee_id: Required[int]
  contract_id: Required[int]
  issuer_id: Required[int]

  date_accepted: str
  date_completed: str
  date_expired: Required[str]
  date_issued: Required[str]

  for_corporation: Required[bool]

  start_location_id: int
  end_location_id: int

  status: Required[ContractStatus]
  type: Required[ContractType]

  title: str

  price: float
  reward: float


class ESIItem(TypedDict, total=False):
  is_included: Required[bool]
  is_singleton: Required[bool]
  quantity: Required[int]
  record_id: Required[int]
  type_id: Required[int]


@corp_auth
def get_corp_contracts(self, corp_id: int) -> list[ESIContract]:
  response = self._get(f'corporations/{corp_id}/contracts/')

  if response.status_code != requests.codes.ok:
    return []

  contracts: list[Any] = response.json()

  remaining_pages = response.headers.get('x-pages')
  logger.info(f'{remaining_pages} pages of contracts to fetch')

  if remaining_pages:
    for page in range(2, int(remaining_pages) + 1):
      self._get(f'corporations/{corp_id}/contracts/', params={'page': page})

      if response.status_code != requests.codes.ok:
        continue  # TODO: Retry

      contracts.extend(response)

  print(f'Fetched {len(contracts)} contracts')
  return contracts


@corp_auth
def get_corp_contract_items(self, corp_id: int, contract_id: int) -> list[ESIItem]:
  response = self._get(f'corporations/{corp_id}/contracts/{contract_id}/items/')
  logger.info(f'Fetched items for contract {contract_id}')
  return response


@corp_auth
def open_corp_contract(self, contract_id: int):
  self._post("ui/openwindow",
                        params={"contract_id": contract_id},)