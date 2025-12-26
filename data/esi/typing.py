from typing import NewType

EntityID = NewType("EntityID", int)
CharacterID = NewType("CharacterID", EntityID)
CorporationID = NewType("CorporationID", EntityID)
AllianceID = NewType("AllianceID", EntityID)
StructureID = NewType("StructureID", int)
TypeID = NewType("TypeID", int)
ContractID = NewType("ContractID", int)
FactionID = NewType("FactionID", int)

def make_character_id(id: int) -> CharacterID:
    return CharacterID(EntityID(id))