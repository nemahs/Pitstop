from typing import Any, cast
from logging import Logger

from flask import Blueprint, redirect, request
from valkey import Valkey

from database import Structure
import sqlalchemy as sa
import sqlalchemy.orm as so

from .dataclasses import NamedItem, UserID, BaseID
from .fetcher import get_key
from data.esi import ESI
from data.esi.esi import get_structure_names
from auth import admin_permissions


logger = Logger(__name__)
STATION_KEY: str = "stations"

def create_station_blueprint(esi: ESI, valkey_client: Valkey, sql: sa.Engine) -> Blueprint:
    station_endpoints = Blueprint("stations", __name__)

    @station_endpoints.get("/")
    def get_stations() -> list[NamedItem]:
        stations = cast(set[str], valkey_client.smembers(STATION_KEY))
        stations = {int(x) for x in stations}

        with so.Session(sql) as session:
            station_names = session.execute(sa.select(Structure.id, Structure.name).where(Structure.id.in_(stations))).all()
            missing_station_names = stations - {x for x,_ in station_names}
            station_names = { BaseID(int(x)): val for x,val in station_names }

            character_id: int = cast(int, valkey_client.srandmember("characters"))
            character_id = UserID(BaseID(character_id))
            access_token = get_key(esi, character_id, valkey_client)

            new_names = get_structure_names(list(missing_station_names), access_token)
            new_names = {BaseID(int(x)): y for x,y in new_names.items()}
            station_names.update(new_names)

        return [NamedItem(name, key) for key, name in station_names.items()]

    @admin_permissions.require()
    @station_endpoints.post("/<int:station_id>")
    def add_station(station_id: int):
        valkey_client.sadd(STATION_KEY, station_id)

        return redirect(request.referrer, code=303)


    @admin_permissions.require()
    @station_endpoints.delete("/<int:station_id>")
    def remove_station(station_id: int):
        valkey_client.srem(STATION_KEY, station_id)

        return redirect(request.referrer, code=303)

    return station_endpoints