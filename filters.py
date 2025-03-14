import valkey
import logging
from flask import Blueprint, request, redirect, url_for, make_response
from flask_principal import RoleNeed, Permission
from flask_login import login_required

class FiltersBlueprint(Blueprint):
    def __init__(self, name: str, import_name: str):
        super().__init__(name, import_name)

    def create_valkey_client(self, host: str) -> None:
        self.valkey_client = valkey.Valkey(host=host)

VALKEY_KEY = "filters"
admin_permissions = Permission(RoleNeed("Admin"))

filters_endpoints = FiltersBlueprint("filters", __name__)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@login_required
@admin_permissions.require()
@filters_endpoints.post("/")
def add_filter():
    filters_endpoints.valkey_client.sadd(VALKEY_KEY, request.data)
    return redirect("/admin", code=303)

@login_required
@admin_permissions.require()
@filters_endpoints.delete("/")
def remove_filter():

    if request.json:
        to_remove = request.json['filter']

        logger.debug("Attempting to remove %s", to_remove)
        keys_removed = filters_endpoints.valkey_client.srem(VALKEY_KEY, to_remove)
        logger.debug("%d keys removed", keys_removed)

    return redirect("/admin", code=303)