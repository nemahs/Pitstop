from .utils import ESIError as ESIError


class ESI():

    def __init__(self, base_url: str = "https://esi.evetech.net/latest", base_headers: dict[str, str] | None = None):
        self.base_url = base_url
        self.base_headers = base_headers

    def _get(self, endpoint: str, params: dict[str, str] | None = None, headers: dict[str, str] = {}):
        import requests
        url = f"{self.base_url}/{endpoint}"
        headers.update(self.base_headers or {})
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            raise ESIError(f"ESI request failed with status {response.status_code}: {response.text}")
        return response.json()

    def _post(self, endpoint: str, params: dict[str, str] | None, json: dict | None = None, headers: dict[str, str] = {}):
        import requests
        url = f"{self.base_url}/{endpoint}"
        headers.update(self.base_headers or {})
        response = requests.post(url, headers=headers, json=json, params=params)
        if response.status_code != 200:
            raise ESIError(f"ESI request failed with status {response.status_code}: {response.text}")
        return response.json()

    from .character import get_alliances_for_characters, get_character_alliance, get_character_corp
    from .corporation import (
        ContractType,
        ESIContract,
        ESIItem,
        get_corp_contract_items,
        get_corp_contracts,
        open_corp_contract,
    )
    from .esi import get_bulk_names, get_structure_names
