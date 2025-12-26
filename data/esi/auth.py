import requests

from ..data_source import OauthTokens
from ..typing import RefreshToken
from .utils import ESIError

TOKEN_URL = "https://login.eveonline.com/v2/oauth/token"


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


def get_tokens(self, code: str) -> OauthTokens:
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
        },
        auth=self.client_auth,
    ).json()

    if "access_token" not in response or "refresh_token" not in response or "expires_in" not in response:
        raise ESIError(f"Missing item in token response, got {response}")

    return OauthTokens(response["access_token"], response["refresh_token"], int(response["expires_in"]))


def refresh_tokens(self, refresh_token: RefreshToken) -> OauthTokens:
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        auth=self.client_auth,
    )

    if response.status_code != requests.codes.ok:
        raise ESIError(f"Failed to refresh tokens, got {response.status_code}: {response.text}")

    response = response.json()
    if "access_token" not in response or "expires_in" not in response:
        raise ESIError(f"Missing item in token response, got {response}")
    return OauthTokens(response["access_token"], None, response["expires_in"])
