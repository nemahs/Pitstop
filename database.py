from datetime import datetime
from enum import Enum, auto
from typing import Generic, TypeVar

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from data.esi.typing import AllianceID, CharacterID, ContractID, CorporationID, EntityID, StructureID, TypeID


class Base(DeclarativeBase):
  type_annotation_map = {int: sa.BIGINT}


class ContractStatus(str, Enum):
  OUTSTANDING = "outstanding"
  IN_PROGRESS = "in_progress"
  FINISHED = "finished"
  CANCELLED = "cancelled"
  REJECTED = "rejected"
  FAILED = "failed"
  DELETED = "deleted"
  EXPIRED = "expired"
  UNKNOWN = "unknown"
  FINISHED_ISSUER = "finished_issuer"
  FINISHED_CONTRACTOR = "finished_contractor"


class EntityType(Enum):
  CHARACTER = auto()
  CORPORATION = auto()
  ALLIANCE = auto()
  UNKNOWN = auto()


NamableIDs = TypeVar("NamableIDs", EntityID, CorporationID, AllianceID, TypeID, StructureID, CharacterID)


class NamedMixin(Generic[NamableIDs]):
  id: Mapped[NamableIDs] = mapped_column(sa.BigInteger, primary_key=True)
  name: Mapped[str] = mapped_column(sa.String(100), unique=True)


class Structure(NamedMixin[StructureID], Base):
  __tablename__ = "structures"


class Alliance(NamedMixin[AllianceID], Base):
  __tablename__ = "alliances"


class ContractEntity(NamedMixin[EntityID], Base):
  __tablename__ = "contract_entities"

  type: Mapped[EntityType]
  alliance_id: Mapped[AllianceID | None] = mapped_column(sa.ForeignKey("alliances.id"))
  alliance: Mapped[Alliance] = relationship()
  updated_at: Mapped[datetime | None] = mapped_column(sa.DateTime)


class ItemType(NamedMixin[TypeID], Base):
  __tablename__ = "item_types"


class ContractItem(Base):
  __tablename__ = "items"

  type_id: Mapped[TypeID] = mapped_column(sa.ForeignKey("item_types.id"), primary_key=True)
  contract_id: Mapped[ContractID] = mapped_column(sa.ForeignKey("contracts.contract_id"), primary_key=True)
  requested: Mapped[bool] = mapped_column(primary_key=True)
  quantity: Mapped[int]

  type: Mapped[ItemType] = relationship()
  contract: Mapped["Contract"] = relationship(back_populates="items")


class Contract(Base):
  __tablename__ = "contracts"

  contract_id: Mapped[ContractID] = mapped_column(primary_key=True)
  contractor_id: Mapped[EntityID] = mapped_column(sa.ForeignKey("contract_entities.id"))
  contracted_to: Mapped[EntityID] = mapped_column(sa.ForeignKey("contract_entities.id"))
  location_id: Mapped[StructureID] = mapped_column(sa.ForeignKey("structures.id"))
  fueller_id: Mapped[EntityID | None] = mapped_column(sa.ForeignKey("contract_entities.id"))
  description: Mapped[str | None] = mapped_column(sa.String(200))
  created_on: Mapped[datetime]
  filled_on: Mapped[datetime | None]
  expires_on: Mapped[datetime | None]
  status: Mapped[ContractStatus] = mapped_column(default=ContractStatus.UNKNOWN)

  items: Mapped[list[ContractItem]] = relationship(back_populates="contract")
  contractor: Mapped[ContractEntity] = relationship("ContractEntity", foreign_keys="Contract.contractor_id")
  assignee: Mapped[ContractEntity] = relationship("ContractEntity", foreign_keys="Contract.contracted_to")
  fueller: Mapped[ContractEntity] = relationship(foreign_keys=[fueller_id])
  structure: Mapped[Structure] = relationship()
