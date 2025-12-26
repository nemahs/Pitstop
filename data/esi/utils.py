from typing import Final


class ESIError(Exception):
    def __init__(self, *args: object, error_code: int | None = None, headers = None) -> None:
        super().__init__(*args)
        self.error_code = error_code
        self.headers = headers


def cached(func):
    def wrapper(self, *args, **kwargs):
        if self.cache:
            pass

        return func(*args, **kwargs)

    return wrapper

def auth_headers(access_token) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "X-Compatibility-Date": "2025-12-09", # TODO: The common headers need to be reworked
    }

ESI_BASE_URL: Final[str] = "https://esi.evetech.net/latest"