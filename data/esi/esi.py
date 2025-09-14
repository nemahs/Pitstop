import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from data.esi.utils import character_auth

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

def get_bulk_names(self, ids: Sequence[int]) -> dict[int, Name]:
    BATCH_SIZE = 500
    output = {}

    if not ids:
        return output

    for i in range(0, (len(ids) // BATCH_SIZE) + 1):
        start_index = i * BATCH_SIZE
        end_index = start_index + (BATCH_SIZE - 1)
        response  = self._post("universe/names",
            json=json.dumps(ids[start_index:end_index])
        )

        output.update({id["id"]: Name(name=id["name"], category=id["category"]) for id in response})

    return output


@character_auth
def get_structure_names(self, ids: Sequence[int]) -> dict[int, str]:
    # All location numbers above this are player structures, all below are stations
    STRUCTURE_ID_START: int = 1000000000

    # Get station names through the normal bulk endpoint
    output = {x: y.name for x,y in self.get_bulk_names([id for id in ids if id < STRUCTURE_ID_START]).items()}

    ids = [id for id in ids if id >= STRUCTURE_ID_START]

    for id in ids:
        response = self._get(f"universe/structures/{id}/")
        output[id] = response["name"]

    return output


def parseRFC7231Date(date_string: str) -> datetime:
    return datetime.strptime(date_string, r"%Y-%m-%dT%H:%M:%SZ")
