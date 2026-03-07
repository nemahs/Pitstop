from collections.abc import Callable
from enum import Enum
from typing import Any, Final, cast

from valkey import Valkey

from .dataclasses import Contract
from .stations import STATION_KEY

type FilterFunction = Callable[[Contract, Any | None], bool]
ISOTOPE_IDS: Final[list[int]] = [16274, 17887, 17888, 17889]


class FilterFunctions(str, Enum):
  INFO_POPULATED = "infoPopulated"
  FUEL_IN_RANGE = "fuelHigh"
  FUEL_ROUNDING = "fuelRounding"
  STRONT_HIGH = "strontHigh"
  VALID_ALLIANCE = "allianceCheck"
  VALID_STATION = "validStation"
  IS_RORQ = "rorqCheck"


def filter_functions(valkey_client: Valkey) -> dict[str, FilterFunction]:
  def fuelInRange(contract: Contract, max: int | None) -> bool:
    if not max:
      return True

    fuel_items = [item for item in contract.items if item.item_type.id in ISOTOPE_IDS]

    for fuel in fuel_items:
      if fuel.quantity >= max:
        return False

    return True

  def isInfoPopulated(contract: Contract, _: Any | None) -> bool:
    return contract.description is not None and len(contract.description.strip()) > 0

  def isRorqContract(contract: Contract, _: Any | None) -> bool:
    return "rorq" in contract.description.lower()

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

    total_stront: int = sum(item.quantity for item in contract.items if item.item_type.id == STRONT_ID)

    return total_stront < max

  def inAllowedAlliances(contract: Contract, alliance_ids: list[str] | None) -> bool:
    if not alliance_ids:
      return True

    return contract.alliance is None or str(contract.alliance.id) in alliance_ids

  def inValidStation(contract: Contract, _: Any | None) -> bool:
    fuelling_stations: set[str] = cast(set[str], valkey_client.smembers(STATION_KEY))

    return not fuelling_stations or contract.location.id in map(int, fuelling_stations)

  return {
    FilterFunctions.INFO_POPULATED: isInfoPopulated,
    FilterFunctions.FUEL_IN_RANGE: fuelInRange,
    FilterFunctions.FUEL_ROUNDING: isFuelRounded,
    FilterFunctions.STRONT_HIGH: isStrontHigh,
    FilterFunctions.VALID_ALLIANCE: inAllowedAlliances,
    FilterFunctions.VALID_STATION: inValidStation,
    FilterFunctions.IS_RORQ: isRorqContract,
  }
