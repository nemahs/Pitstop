from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class ProgramConfig(BaseSettings):
    """
    Configuration for the application.
    """

    model_config = SettingsConfigDict(
        extra="allow",
    )

    CLIENT_ID: str
    CLIENT_SECRET: str
    AUTH_TYPE: Literal["gice", "esi"]
    REDIRECT_URI: str

    GROUP_ID: int
    
    SCOPES: list[str] = []

    VALKEY_HOST: str = "localhost"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str