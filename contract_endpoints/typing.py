from typing import NewType
from typing import NotRequired
from data.esi.corporation import ESIContract, ESIItem

BaseID = NewType("BaseID", int)
UserID = NewType("UserID", BaseID)
CorpID = NewType("CorpID", BaseID)
ContractID = NewType("ContractID", BaseID)
StructureID = NewType("StructureID", BaseID)
TypeID = NewType("TypeID", BaseID)


class EnrichedContract(ESIContract, total=False):
    assignee_name: str
    issuer_name: str
    location_name: str
    type_name: str
    alliance: int | None

class EnrichedItem(ESIItem, total=False):
    name: NotRequired[str]
