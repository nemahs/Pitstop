from enum import IntFlag, auto, verify, UNIQUE

import valkey

from .data.typing import AccessToken, RefreshToken
from flask_principal import Permission, RoleNeed

@verify(UNIQUE)
class Permissions(IntFlag):
    Admin = auto()


admin_permissions = Permission(RoleNeed("Admin"))

class AuthManager:
    def __init__(self, host: str = "localhost"):
        self.valkey_client = valkey.Valkey(host=host)

    def save_user(self, user_id: int, access_token: AccessToken, refresh_token: RefreshToken, expiry: int, name: str):
        self.valkey_client.sadd("characters", user_id)
        self.valkey_client.set(f"{user_id}:access_token", access_token, ex=expiry)
        self.valkey_client.set(f"{user_id}:refresh_token", refresh_token)
        self.valkey_client.set(f"{user_id}:name", name)

    def get_user(self, user_id):
        name_data = self.valkey_client.get(f"{user_id}:name")

        if not name_data:
            return User(user_id, "Unknown username")

        assert isinstance(name_data, bytes)
        name: str = name_data.decode("utf-8")
        return User(user_id, name)


class User:
    def __init__(self, id, name: str | None = None):
        self.id = id
        self.name = name
        self.is_active = True
        self.is_authenticated = True

    def get_id(self):
        return self.id
