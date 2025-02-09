from dataclasses import dataclass
from typing import Protocol

from valkey import Valkey

from .typing import AccessToken, RefreshToken


@dataclass
class OauthTokens:
    access_token: AccessToken
    refresh_token: RefreshToken | None
    expiry: int


class DataSource(Protocol):
    def __init__(self, client_id: str, client_secret: str, cache: Valkey | None = None) -> None: ...
    def get_contracts(self, corp_id: int): ...

    # Auth (Maybe move to its own object?)
    def get_tokens(self, code: str) -> OauthTokens: ...
    def refresh_tokens(self, refresh_token: RefreshToken) -> OauthTokens: ...
