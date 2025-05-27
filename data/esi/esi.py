from dataclasses import dataclass
from enum import Enum
import json
import logging
from datetime import datetime
from collections.abc import Sequence

import requests

from ..typing import AccessToken

logger = logging.getLogger(__name__)

class ESIEntity(str, Enum):
    ALLIANCE = "alliance"
    CORPORATION = "corporation"
    CONSTELLATION = "constellation"
    CHARACTER = "character"
    INVENTORY = "inventory"
    REGION = "region"
    SOLAR_SYSTEM = "solar_system"
    STATION = "station"
    FACTION = "faction"

@dataclass
class Name:
    name: str
    category: ESIEntity

def get_bulk_names(ids: Sequence[int]) -> dict[int, Name]:
    BATCH_SIZE = 500
    output = {}

    if not ids:
        return output

    for i in range(0, (len(ids) // BATCH_SIZE) + 1):
        start_index = i * BATCH_SIZE
        end_index = start_index + (BATCH_SIZE - 1)
        response = requests.post(
            "https://esi.evetech.net/latest/universe/names/", data=json.dumps(ids[start_index:end_index])
        )

        if response.status_code != requests.codes.ok:
            logger.error(
                f"Error occurred while fetching bulk names, response code {response.status_code}, text {response.text}"
            )
            continue

        output.update({id["id"]: Name(name=id["name"], category=id["category"]) for id in response.json()})

    return output


def get_structure_names(ids: Sequence[int], access_token: AccessToken) -> dict[int, str]:
    # All location numbers above this are player structures, all below are stations
    STRUCTURE_ID_START: int = 1000000000

    # Get station names through the normal bulk endpoint
    output = {x: y.name for x,y in get_bulk_names([id for id in ids if id < STRUCTURE_ID_START]).items()}

    ids = [id for id in ids if id >= STRUCTURE_ID_START]

    for id in ids:
        response = requests.get(
            f"https://esi.evetech.net/latest/universe/structures/{id}/",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code != requests.codes.ok:
            logger.error(
                f"Error occurred while fetching structure {id}, response code {response.status_code}, text {response.text}"
            )

            if response.status_code == requests.codes.unauthorized:
                logger.error("Key expired, skipping remaining structures")
                break

            continue

        output[id] = response.json()["name"]

    return output


def parseRFC7231Date(date_string: str) -> datetime:
    return datetime.strptime(date_string, r"%Y-%m-%dT%H:%M:%SZ")
