import requests
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARN)

BASE_URL = "https://esi.evetech.net/latest"


def get_character_corp(self, character_id: int) -> int:
    """
    Get the corporation id of a character.
    """

    response = requests.post(BASE_URL + "/characters/affiliation/", json=[str(character_id)])

    return response.json()[0]["corporation_id"]


def get_character_alliance(self, character_id: int) -> int | None:

    response = requests.get(BASE_URL + f"/characters/{character_id}/")

    if response.status_code != requests.status_codes.codes.OK:
        logger.warning("Error returned while getting character alliance, got %s", response.text)
        return None

    return response.json()["alliance_id"]