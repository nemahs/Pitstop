from typing import override

from contract_endpoints.dataclasses import NamedItem
from contract_endpoints.filters import *

functions = filter_functions(None) # type: ignore


def test_fuel_in_range():
  class MockItem:
    def __init__(self, item_type_id, quantity):
      self.item_type = type("obj", (object,), {"id": item_type_id})
      self.quantity = quantity

  class MockContract(Contract):
    def __init__(self, items):
      self.items = items

  contract = MockContract(
    items=[
      MockItem(item_type_id=16274, quantity=50),
      MockItem(item_type_id=17887, quantity=100),
      MockItem(item_type_id=17889, quantity=30),
      MockItem(item_type_id=99999, quantity=200),  # Non-fuel item
    ]
  )

  assert functions[FilterFunctions.FUEL_IN_RANGE](contract, 40) == False
  assert functions[FilterFunctions.FUEL_IN_RANGE](contract, 60) == False
  assert functions[FilterFunctions.FUEL_IN_RANGE](contract, 100) == False
  assert functions[FilterFunctions.FUEL_IN_RANGE](contract, 120) == True
  assert functions[FilterFunctions.FUEL_IN_RANGE](contract, 200) == True
  assert functions[FilterFunctions.FUEL_IN_RANGE](contract, None) == True


def test_is_info_populated():
  class MockContract(Contract):
    def __init__(self, description):
      self.description = description

  contract_with_info = MockContract(description="This is a contract description.")
  contract_without_info = MockContract(description="")
  contract_none_info = MockContract(description=None)
  contract_only_spaces = MockContract(description="   ")

  assert functions[FilterFunctions.INFO_POPULATED](contract_with_info, None) == True
  assert functions[FilterFunctions.INFO_POPULATED](contract_without_info, None) == False
  assert functions[FilterFunctions.INFO_POPULATED](contract_none_info, None) == False
  assert functions[FilterFunctions.INFO_POPULATED](contract_only_spaces, None) == False


def test_is_fuel_rounded():
  class MockItem:
    def __init__(self, item_type_id, quantity):
      self.item_type = type("obj", (object,), {"id": item_type_id})
      self.quantity = quantity

  class MockContract(Contract):
    def __init__(self, items):
      self.items = items

  contract = MockContract(
    items=[
      MockItem(item_type_id=16274, quantity=100),
      MockItem(item_type_id=17887, quantity=250),
      MockItem(item_type_id=17889, quantity=75),
      MockItem(item_type_id=99999, quantity=203),  # Non-fuel item
    ]
  )

  assert functions[FilterFunctions.FUEL_ROUNDING](contract, 25) == True
  assert functions[FilterFunctions.FUEL_ROUNDING](contract, 50) == False
  assert functions[FilterFunctions.FUEL_ROUNDING](contract, 100) == False
  assert functions[FilterFunctions.FUEL_ROUNDING](contract, None) == True

def test_is_stront_high():
  class MockItem:
    def __init__(self, item_type_id, quantity):
      self.item_type = type("obj", (object,), {"id": item_type_id})
      self.quantity = quantity

  class MockContract(Contract):
    def __init__(self, items):
      self.items = items

  contract = MockContract(
    items=[
      MockItem(item_type_id=16275, quantity=30),  # Strontium-90
      MockItem(item_type_id=16275, quantity=25),  # Strontium-90
      MockItem(item_type_id=17887, quantity=100),  # Non-Strontium fuel
    ]
  )

  assert functions[FilterFunctions.STRONT_HIGH](contract, 40) == False
  assert functions[FilterFunctions.STRONT_HIGH](contract, 55) == False
  assert functions[FilterFunctions.STRONT_HIGH](contract, 70) == True
  assert functions[FilterFunctions.STRONT_HIGH](contract, 100) == True
  assert functions[FilterFunctions.STRONT_HIGH](contract, None) == True


def test_in_allowed_alliances():
  class MockContract(Contract):
    def __init__(self, alliance):
      self.alliance = alliance

  class MockAlliance:
    def __init__(self, id):
      self.id = id

  contract_in_alliance = MockContract(alliance=MockAlliance(id="123"))
  contract_in_second_alliance = MockContract(alliance=MockAlliance(id="789"))
  contract_not_in_alliance = MockContract(alliance=MockAlliance(id="456"))
  contract_no_alliance = MockContract(alliance=None)

  allowed_alliances = ["123", "789"]

  assert functions[FilterFunctions.VALID_ALLIANCE](contract_in_alliance, allowed_alliances) == True
  assert functions[FilterFunctions.VALID_ALLIANCE](contract_in_second_alliance, allowed_alliances) == True
  assert functions[FilterFunctions.VALID_ALLIANCE](contract_not_in_alliance, allowed_alliances) == False
  assert functions[FilterFunctions.VALID_ALLIANCE](contract_no_alliance, allowed_alliances) == True
  assert functions[FilterFunctions.VALID_ALLIANCE](contract_in_alliance, None) == True


def test_in_valid_station():
  class MockContract(Contract):
    def __init__(self, location_id):
      self.location = NamedItem(id=location_id, name="Mock Station")

  contract_in_valid_station = MockContract(location_id=1001)
  contract_in_other_valid_station = MockContract(location_id=1003)
  contract_not_in_valid_station = MockContract(location_id=2002)

  # Mocking the valkey_client behavior
  class MockValkeyClient(Valkey):
    @override
    def smembers(self, name):
      return {"1001", "1003", "1005"}

  mock_valkey_client = MockValkeyClient()
  functions_with_mock = filter_functions(mock_valkey_client)
  
  class MockEmptyValkeyClient(Valkey):
    @override
    def smembers(self, name):
      return set()

  functions_with_empty_mock = filter_functions(MockEmptyValkeyClient())

  assert functions_with_mock[FilterFunctions.VALID_STATION](contract_in_valid_station, None) == True
  assert functions_with_mock[FilterFunctions.VALID_STATION](contract_in_other_valid_station, None) == True
  assert functions_with_mock[FilterFunctions.VALID_STATION](contract_not_in_valid_station, None) == False
  assert functions_with_empty_mock[FilterFunctions.VALID_STATION](contract_not_in_valid_station, None) == True