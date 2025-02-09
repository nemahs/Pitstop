import requests

BASE_URL = "https://esi.evetech.net/latest"


def get_character_corp(self, character_id: int) -> int:
    """
    Get the corporation id of a character.
    """

    response = requests.post(BASE_URL + "/characters/affiliation/", json=[str(character_id)])

    return response.json()[0]["corporation_id"]
