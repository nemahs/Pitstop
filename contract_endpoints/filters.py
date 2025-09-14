from collections.abc import Callable
from typing import Any, cast

from valkey import Valkey

from .dataclasses import Contract
from .stations import STATION_KEY

type FilterFunction = Callable[[Contract, Any | None], bool]

ISOTOPE_IDS = [16274, 17887, 17888, 17889]

def filter_functions(valkey_client: Valkey) -> dict[str, FilterFunction]:
  def fuelInRange(contract: Contract, max: int | None) -> bool:
    fuel_items = [item for item in contract.items if item.item_type.id in ISOTOPE_IDS]

    if not max:
      return True

    for fuel in fuel_items:
      if fuel.quantity >= max:
        return False

    return True

  def isInfoPopulated(contract: Contract, _: Any | None) -> bool:
    return contract.description is not None and len(contract.description) > 0

  def isFuelRounded(contract: Contract, roundingValue: int | None) -> bool:

    if not roundingValue:
      return True

    fuel_items = [item for item in contract.items if item.item_type.id in ISOTOPE_IDS]

    for fuel in fuel_items:
      if fuel.quantity % roundingValue != 0:
        return False

    return True

  def isStrontHigh(contract: Contract, max: int | None) -> bool:
    STRONT_ID = 16275

    if not max:
      return True

    total_stront: int = sum([item.quantity for item in contract.items if item.item_type.id == STRONT_ID])

    return total_stront < max

  def inAllowedAlliances(contract: Contract, alliance_ids: list[str] | None) -> bool:
    if not alliance_ids:
      return True

    return contract.alliance is None or str(contract.alliance.id) in alliance_ids

  def inValidStation(contract: Contract, _: Any | None) -> bool:
    fuelling_stations: set[str] = cast(set[str], valkey_client.smembers(STATION_KEY))
    valid_stations: list[int] = [int(x) for x in fuelling_stations]

    return len(fuelling_stations) == 0 or contract.location.id in valid_stations

  return {
    'infoPopulated': isInfoPopulated,
    'fuelHigh': fuelInRange,
    'fuelRounding': isFuelRounded,
    'strontHigh': isStrontHigh,
    'allianceCheck': inAllowedAlliances,
    'validStation': inValidStation,
  }
