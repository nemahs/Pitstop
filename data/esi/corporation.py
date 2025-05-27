import logging
from enum import Enum
from typing import Any, Required, TypedDict

import requests

from ..typing import AccessToken
from .utils import ESIError, ESI_BASE_URL, auth_headers

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

def get_corp_contracts(_, corp_id: int, access_token: AccessToken) -> list[ESIContract]:
    response = requests.get(
        f"{ESI_BASE_URL}/corporations/{corp_id}/contracts/",
        headers=auth_headers(access_token),
    )

    if response.status_code != requests.codes.ok:
        return []

    contracts: list[Any] = response.json()

    remaining_pages = response.headers.get("x-pages")
    logger.info(f"{remaining_pages} pages of contracts to fetch")

    if remaining_pages:
        for page in range(2, int(remaining_pages) + 1):
            response = requests.get(
                f"{ESI_BASE_URL}/corporations/{corp_id}/contracts/?page={page}",
                headers=auth_headers(access_token),
            )

            if response.status_code != requests.codes.ok:
                continue  # TODO: Retry

            contracts.extend(response.json())

    print(f"Fetched {len(contracts)} contracts")
    return contracts


def get_corp_contract_items(_, corp_id: int, contract_id: int, access_token: AccessToken) -> list[ESIItem]:
    response = requests.get(
        f"{ESI_BASE_URL}/corporations/{corp_id}/contracts/{contract_id}/items/",
        headers=auth_headers(access_token),
    )

    if response.status_code != 200:
        logger.error(f"Error occurred while fetching items for {contract_id}, response code {response.status_code}")
        raise ESIError(response.status_code, "Failed to get items for contract")

    logger.info(f"Fetched items for contract {contract_id}")
    return response.json()


def open_corp_contract(contract_id: int, access_token: AccessToken):
    response = requests.post(f"{ESI_BASE_URL}/ui/openwindow/contract?contract_id={contract_id}",
                             headers=auth_headers(access_token))
    

    if response.status_code != requests.status_codes.codes.OK:
        logger.error(f"Error occurred trying to open contract window, code: {response.status_code}, text: {response.text}")
