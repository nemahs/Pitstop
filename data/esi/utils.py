import functools


class ESIError(Exception):
    def __init__(self, *args: object, error_code: int | None = None) -> None:
        super().__init__(*args)
        self.error_code = error_code


def cached(func):
    def wrapper(self, *args, **kwargs):
        if self.cache:
            pass

        return func(*args, **kwargs)

    return wrapper

def auth_headers(access_token) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}"
    }


# TODO: These are specific to GICE, need to implement an ESI version and allow for toggling by AUTH_TYPE
def character_auth(func):
    def wrapper(self, *args, character_id: int, **kwargs):
        functools.wraps(func)
        self.base_headers = {
            "X-Character_Id": character_id,
            "X-Token-Type": "P"
        }

        return func(*args, **kwargs)
    return wrapper

def corp_auth(func):
    def wrapper(self, *args, corp_id: int, **kwargs):
        functools.wraps(func)
        self.base_headers = {
            "X-Entity_Id": corp_id,
            "X-Token-Type": "C"
        }

        return func(*args, **kwargs)
    return wrapper