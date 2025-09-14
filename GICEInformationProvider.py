from flask import Flask
from flask_principal import identity_loaded, RoleNeed, Identity

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class GICEInformationProvider():
    def __init__(self, app: Flask, gice_client_id: str, gice_client_secret: str):
        self.gice_client_id = gice_client_id
        self.gice_client_secret = gice_client_secret
        identity_loaded.connect(self.provide_information, app)

    def provide_information(self, sender, identity: Identity):
        logger.debug(f"Called to provide information from {str(sender)}")

        # Here you would typically fetch permissions or roles from GICE
        # For demonstration purposes, we will just add a dummy role
        identity.provides.add(RoleNeed("gice_user"))
        logger.debug(f"Adding 'gice_user' role to user {identity.id}")