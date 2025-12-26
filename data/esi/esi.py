import itertools
import logging
import time
from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from typing import Final, Literal

import requests
from pydantic import BaseModel, TypeAdapter

from data.esi.character import BASE_URL
from data.esi.typing import CorporationID
from data.esi.utils import auth_headers

from ..typing import AccessToken

logger = logging.getLogger(__name__)


class ESIEntity(str, Enum):
  ALLIANCE = "alliance"
  CHARACTER = "character"
  CONSTELLATION = "constellation"
  CORPORATION = "corporation"
  INVENTORY = "inventory_type"
  REGION = "region"
  SOLAR_SYSTEM = "solar_system"
  STATION = "station"
  FACTION = "faction"


class Name(BaseModel):
  name: str
  category: ESIEntity
  id: int

class Point(BaseModel):
  x: float
  y: float
  z: float

class Structure(BaseModel):
  name: str
  owner_id: CorporationID
  position: Point
  solar_system_id: int
  type_id: int | None = None

def get_bulk_names(ids: Sequence[int]) -> dict[int, Name]:
  NameList = TypeAdapter(list[Name])
  BATCH_SIZE: Literal[500] = 500 # Batch size limit imposed by ESI
  output = {}

  if not ids:
    return output

  for batch in itertools.batched(ids, BATCH_SIZE):
    response = requests.post(BASE_URL + "/universe/names/", json=batch)

    if response.status_code != requests.codes.ok:
      logger.error(
        "Error occurred while fetching bulk names, response code %d, text %s", response.status_code, response.text
      )
      continue

    output.update({id.id: id for id in NameList.validate_json(response.text)})

  return output


def get_structure_names(ids: Sequence[int], access_token: AccessToken) -> dict[int, str]:
  # All location numbers above this are player structures, all below are stations
  STRUCTURE_ID_START: Final[int] = 1000000000

  # Get station names through the normal bulk endpoint
  output = {x: y.name for x, y in get_bulk_names([id for id in ids if id < STRUCTURE_ID_START]).items()}

  structure_ids = [id for id in ids if id >= STRUCTURE_ID_START]

  for id in structure_ids:
    response = requests.get(f"{BASE_URL}/universe/structures/{id}/", headers=auth_headers(access_token))

    match response.status_code:
      case requests.codes.ok:
        structure = Structure.model_validate_json(response.text)
        output[id] = structure.name
      case requests.codes.unauthorized:
        logger.error("Key expired, skipping remaining structures")
        break
      case requests.codes.too_many:
        logger.warning("Rate limited, waiting before continuing")
        time.sleep(int(response.headers.get("Retry-After", 1)))
      case _:
        logger.error(
          f"Error occurred while fetching structure {id}, response code {response.status_code}, text {response.text}"
        )
  return output


def parseRFC7231Date(date_string: str) -> datetime:
  return datetime.strptime(date_string, r"%Y-%m-%dT%H:%M:%SZ")
