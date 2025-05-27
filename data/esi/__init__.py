from requests.auth import HTTPBasicAuth
from valkey import Valkey

from ..data_source import DataSource
from .utils import ESIError as ESIError


class ESI(DataSource):
    def __init__(self, client_id: str, client_secret: str, cache: Valkey | None = None):
        self.client_auth = HTTPBasicAuth(client_id, client_secret)
        self.client_id = client_id
        self.cache = cache

    from .auth import get_tokens, refresh_tokens
    from .character import get_character_corp, get_character_alliance, get_alliances_for_characters
    from .corporation import get_corp_contracts, get_corp_contract_items, ESIContract, ESIItem, ContractType
    from .esi import get_structure_names, get_bulk_names

    def get_contracts(self, corp_id: int):
        raise NotImplementedError
