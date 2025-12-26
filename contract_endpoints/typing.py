from typing import NewType

from data.esi.corporation import ESIContract, ESIItem
from data.esi.typing import AllianceID

UserID = NewType("UserID", int)

class EnrichedContract(ESIContract):
    assignee_name: str
    issuer_name: str
    location_name: str
    type_name: str
    alliance: AllianceID | None

class EnrichedItem(ESIItem):
    name: str
