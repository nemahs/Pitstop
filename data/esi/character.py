import itertools
import logging
from datetime import datetime
from typing import Annotated, Literal

import requests
from pydantic import BaseModel, Field, TypeAdapter

from data.esi.typing import AllianceID, CharacterID, CorporationID, FactionID
from data.esi.utils import ESIError

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARN)

BASE_URL = "https://esi.evetech.net/latest"

class CharacterAffiliation(BaseModel):
    alliance_id: AllianceID | None = None
    character_id: CharacterID
    corporation_id: CorporationID
    faction_id: FactionID | None = None

class CharacterPublicData(BaseModel):
    alliance_id: AllianceID | None = None
    birthday: datetime
    bloodline_id: int
    corporation_id: CorporationID
    description: str | None = None
    faction_id: FactionID | None = None
    gender: Literal["female","male"]
    name: str
    race_id: int
    security_status: Annotated[float, Field(ge=-10,le=10)] | None = None
    title: str | None = None

CharacterAffiliationList = TypeAdapter(list[CharacterAffiliation])

def get_character_corp(_, character_id: CharacterID) -> CorporationID:
    """
    Get the corporation id of a character.
    """

    response = requests.post(BASE_URL + "/characters/affiliation/", json=[str(character_id)])

    if response.status_code in range(500,600):
        raise ESIError("Server error occurred", error_code=response.status_code)


    affiliations = CharacterAffiliationList.validate_json(response.text)

    return affiliations[0].corporation_id


def get_character_alliance(_, character_id: CharacterID) -> AllianceID | None:

    response = requests.get(BASE_URL + f"/characters/{character_id}/")

    if response.status_code != requests.status_codes.codes.OK:
        logger.warning("Error returned while getting character alliance, got %s", response.text)
        return None

    response_data = CharacterPublicData.model_validate_json(response.text)

    return response_data.alliance_id


def get_alliances_for_characters(_, ids: list[CharacterID]) -> dict[CharacterID, AllianceID | None]:
    CHUNK_SIZE = 1000
    output = {}

    for batch in itertools.batched(ids, CHUNK_SIZE):
        logger.debug("Processing batch")
        response = requests.post(BASE_URL + f"/characters/affiliation", json=batch)

        if response.status_code != requests.codes.ok:
            logger.warning("Error while getting alliances, got %s", response.text)

        for item in CharacterAffiliationList.validate_json(response.text):
            if item.character_id not in output:
                output[item.character_id] = item.alliance_id

    return output