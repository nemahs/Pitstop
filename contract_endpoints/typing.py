from typing import NewType

from ..data.esi.corporation import ESIContract

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
