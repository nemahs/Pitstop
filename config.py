from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from data.esi.typing import CorporationID


class ConfigFile(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    AUTH_TYPE: Literal["gice", "esi"]

    CORP_ID: CorporationID
    CLIENT_ID: str
    CLIENT_SECRET: str
    REDIRECT_URI: str

    VALKEY_HOST: str = "localhost"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PASSWORD: str

    SCOPES: str # TODO: Validate against valid ESI scopes