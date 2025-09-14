import datetime
from datetime import timedelta

import requests
from pydantic import BaseModel
from requests_oauthlib import OAuth2Session

from data.data_source import OauthProvider, OAuthTokens, UserData

from ..typing import AccessToken, RefreshToken
from . import ESI
from .utils import ESIError

LOGIN_URL = "https://login.eveonline.com/v2/oauth"

class ESIAuth(OauthProvider):

    class TokenResponse(BaseModel):
        access_token: AccessToken
        refresh_token: RefreshToken | None
        expires_in: timedelta


    def __init__(self, esi: ESI, client_id: str, client_secret: str, redirect_uri: str, scopes: list[str]):
        self.client_secret = client_secret
        self._client = OAuth2Session(client_id=client_id, redirect_uri=redirect_uri, scope=scopes)
        self.esi = esi

    def get_authorization_url(self) -> str:
        authorization_url, self._state = self._client.authorization_url(f"{LOGIN_URL}/authorize")
        return authorization_url

    def login_user(self, code: str) -> OAuthTokens:
        token = self._client.fetch_token(
            f"{LOGIN_URL}/token",
            code=code,
            client_secret=self.client_secret,
        )

        response_data = self.TokenResponse(**token)

        return OAuthTokens(
            access_token=response_data.access_token,
            refresh_token=response_data.refresh_token,
            expires_at=response_data.expires_in + datetime.datetime.now(datetime.UTC)
        )

    def get_user_info(self, access_token: AccessToken) -> UserData:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(f"{LOGIN_URL}/verify", headers=headers)

        if response.status_code != 200:
            raise ESIError(f"Failed to fetch user info: {response.status_code} {response.text}")

        user_info = response.json()
        return UserData(**user_info)

    def refresh_tokens(self, refresh_token: RefreshToken) -> OAuthTokens:
        new_tokens = self._client.refresh_token(f"{LOGIN_URL}/token",
            refresh_token=refresh_token)

        new_token_data = self.TokenResponse(**new_tokens)

        return OAuthTokens(new_token_data.access_token, None, 
                           new_token_data.expires_in + datetime.datetime.now(datetime.UTC))

    def is_user_in_group(self, token: OAuthTokens, group: int) -> bool:
        user_data = self.get_user_info(token.access_token)
        corp_id = self.esi.get_character_corp(user_data.id)
        return corp_id == group



#region Helper Functions

def _get_jwks_uri() -> str:
    SSO_META_DATA_URL = "https://login.eveonline.com/.well-known/oauth-authorization-server"
    data = requests.get(SSO_META_DATA_URL).json()

    return data["jwks_uri"]


def decode_token(token: str):
    import json

    from jwcrypto import jwk, jwt

    jwks = requests.get(_get_jwks_uri())
    jwk_set = jwk.JWKSet.from_json(jwks.text)

    contents = jwt.JWT(jwt=token, key=jwk_set)
    return json.loads(contents.claims)





#endregion