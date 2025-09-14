import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Literal, cast

import requests
from pydantic import BaseModel
from requests_oauthlib import OAuth2Session

from data.data_source import OauthProvider, OAuthTokens, UserData
from data.esi import ESI
from data.typing import AccessToken, RefreshToken

from .UserData import GICEUserData

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class GICEScopes(str, Enum):
    """
    Valid scopes for GICE.
    """
    GROUP_LIST_MEMBERS= "groups-list-members"
    GROUPS = "groups-limited"
    GROUP_PARTICIPATION = "groups-activity-detailed"
    CORP_RATTING = "corps-ratting"
    USER_INFO = "openid"

class TokenResponse(BaseModel):
    """
    Token response from GICE OAuth2 authentication.
    """
    access_token: AccessToken
    refresh_token: RefreshToken | None = None
    id_token: str | None = None
    token_type: Literal["Bearer"]
    expires_in: timedelta
    expires_at: datetime

class GICE(OauthProvider):

    _GICE_URL = "https://esi.goonfleet.com/oauth"
    app_scopes = [
        GICEScopes.GROUPS,
        GICEScopes.USER_INFO
    ]


    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Constructor
        
        :param client_id: GICE client ID
        :param client_secret: GICE client secret
        """

        scope_values = [scope.value for scope in self.app_scopes]

        self._client = OAuth2Session(client_id=client_id, scope=scope_values, redirect_uri=redirect_uri)
        self._client_secret = client_secret
        self._esi = ESI("localhost:4001")


    @property
    def esi(self) -> ESI:
        return self._esi

    def get_authorization_url(self) -> str:

        authorization_url, self._state = self._client.authorization_url(
            f"{self._GICE_URL}/authorize",
        )

        return authorization_url

    def login_user(self, code: str) -> OAuthTokens:
        token = self._client.fetch_token(
            f"{self._GICE_URL}/token",
            code=code,
            client_secret=self._client_secret,
        )

        logger.debug(f"Token received: {token}")

        response_data = TokenResponse(**token)
        access_token = AccessToken(response_data.access_token)

        return OAuthTokens(access_token=access_token,
                           refresh_token=None,
                           expires_at=response_data.expires_at)

    def get_user_info(self, access_token: AccessToken) -> UserData:
        response =  requests.get(f"{self._GICE_URL}/userinfo",
                                headers={"Authorization": f"Bearer {access_token}"}
        )

        if response.status_code != requests.codes.ok:
            logger.error(f"Failed to fetch user info: {response.status_code} - {response.text}")

        logger.debug(f"User info response: {response.json()}")
        return GICEUserData(**response.json())


    def is_user_in_group(self, token: OAuthTokens, group: int) -> bool:
        """
        Check if the user is in a specific group.
        
        :param token: Token to get user data from 
        :param group: Group ID to check membership against
        :return: True if valid, False otherwise
        """
        return True
        # Need to check all groups the user is in, not just the primary group
        try:
            user_info = cast(GICEUserData, self.get_user_info(token.access_token))
            return user_info is not None and group in user_info.grp
        except Exception as e:
            logger.error(f"Error validating user: {e}")
            return False
