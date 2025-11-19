import logging

import valkey
from flask import Flask
from flask_principal import Identity, RoleNeed, identity_loaded

from .auth import Permissions

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ValkeyInformationProvider():
    def __init__(self, app: Flask, valkey_host: str = "localhost"):
        self.valkey_client = valkey.Valkey(host=valkey_host)
        identity_loaded.connect(self.provide_information, app)


    def provide_information(self, sender, identity: Identity):
        logger.debug(f"Called to provide information from {str(sender)}")

        permissions_data = self.valkey_client.get(f"{identity.id}:permissions")
        if permissions_data:
            assert isinstance(permissions_data, bytes), f"Type is {type(permissions_data)}"
            permissions = Permissions(int.from_bytes(permissions_data))
            logger.debug(f"Got {permissions} from Valkey")

            for permission in list(permissions):
                identity.provides.add(RoleNeed(permission.name))
                logger.debug(f"Adding {permission.name} to list of permissions for user {identity.id}")