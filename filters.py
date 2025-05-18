import valkey
import logging
from flask import Blueprint, request, redirect

VALKEY_KEY = "filters"
logger = logging.getLogger(__name__)


def create_filter_endpoints(valkey_client: valkey.Valkey) -> Blueprint:
    filters_endpoints = Blueprint("filters", __name__)

    @filters_endpoints.post("/")
    def add_filter():
        valkey_client.sadd(VALKEY_KEY, request.data)
        return redirect(request.referrer, code=303)


    @filters_endpoints.delete("/")
    def remove_filter():

        if request.json:
            to_remove = request.json['filter']

            logger.debug("Attempting to remove %s", to_remove)
            keys_removed = valkey_client.srem(VALKEY_KEY, to_remove)
            logger.debug("%d keys removed", keys_removed)

        return redirect(request.referrer, code=303)

    return filters_endpoints