from typing import NewType, NotRequired

from data.esi.corporation import ESIContract, ESIItem


class BaseID(int):
    pass

class UserID(BaseID):
    pass

class CorpID(BaseID):
    pass

class ContractID(BaseID):
    pass

class StructureID(BaseID):
    pass

class TypeID(BaseID):
    pass

class EnrichedContract(ESIContract, total=False):
    assignee_name: str
    issuer_name: str
    location_name: str
    type_name: str
    alliance: int | None

class EnrichedItem(ESIItem, total=False):
    name: NotRequired[str]
