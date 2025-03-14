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
    from .character import get_character_corp, get_character_alliance

    def get_contracts(self, corp_id: int):
        raise NotImplementedError
