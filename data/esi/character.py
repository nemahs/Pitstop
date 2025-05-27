import requests
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARN)

BASE_URL = "https://esi.evetech.net/latest"


def get_character_corp(_, character_id: int) -> int:
    """
    Get the corporation id of a character.
    """

    response = requests.post(BASE_URL + "/characters/affiliation/", json=[str(character_id)])

    return response.json()[0]["corporation_id"]


def get_character_alliance(_, character_id: int) -> int | None:

    response = requests.get(BASE_URL + f"/characters/{character_id}/")

    if response.status_code != requests.status_codes.codes.OK:
        logger.warning("Error returned while getting character alliance, got %s", response.text)
        return None

    response_data = response.json()

    return response_data.get("alliance_id", None)


def get_alliances_for_characters(_, ids: list[int]) -> dict[int, int | None]:
    CHUNK_SIZE = 1000
    character_lists = [ids[i:i+CHUNK_SIZE] for i in range(0, len(ids), CHUNK_SIZE)]
    output = {}

    for chunk in character_lists:
        response = requests.post(BASE_URL + f"/characters/affiliation", json=chunk)

        if response.status_code != requests.codes.ok:
            logger.warning("Error while getting alliances, got %s", response.text)

        for item in response.json():
            if "character_id" in item:
                output[item["character_id"]] = int(item["alliance_id"]) if "alliance_id" in item else None

    return output