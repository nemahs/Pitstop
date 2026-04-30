from requests.auth import HTTPBasicAuth
from valkey import Valkey

from ..data_source import DataSource


class ESI(DataSource):
    def __init__(self, client_id: str, client_secret: str, cache: Valkey | None = None):
        self.client_auth = HTTPBasicAuth(client_id, client_secret)
        self.client_id = client_id
        self.cache = cache

    from .auth import get_tokens, refresh_tokens
    from .character import get_alliances_for_characters, get_character_alliance, get_character_corp
    from .corporation import ContractType, ESIContract, ESIItem, get_corp_contract_items, get_corp_contracts
    from .esi import get_bulk_names, get_structure_names

    def get_contracts(self, corp_id: int):
        raise NotImplementedError
