from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel
from valkey import Valkey

from .typing import AccessToken, RefreshToken


@dataclass
class OAuthTokens:
    access_token: AccessToken
    refresh_token: RefreshToken | None
    expires_at: datetime

class UserData(BaseModel):
    name: str
    id: int

class OauthProvider(Protocol):
    def get_authorization_url(self) -> str: ...
    def login_user(self, code: str) -> OAuthTokens: ...
    def get_user_info(self, access_token: AccessToken) -> UserData: ...
    def is_user_in_group(self, token: OAuthTokens, group: int) -> bool: ...

class DataSource(Protocol):
    def __init__(self, client_id: str, client_secret: str, cache: Valkey | None = None) -> None: ...
    def get_contracts(self, corp_id: int): ...