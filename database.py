from datetime import datetime
from enum import Enum, auto

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass

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


class NamedMixin:
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(100), unique=True)


class Structure(NamedMixin, Base):
    __tablename__ = "structures"

class Alliance(NamedMixin, Base):
    __tablename__ = "alliances"

class ContractEntity(NamedMixin, Base):
    __tablename__ = "contract_entities"

    type: Mapped[EntityType]
    alliance_id: Mapped[int | None] = mapped_column(sa.ForeignKey("alliances.id"))
    alliance: Mapped[Alliance] = relationship()

class ItemType(NamedMixin, Base):
    __tablename__ = "item_types"

class ContractItem(Base):
    __tablename__ = "items"

    type_id: Mapped[int] = mapped_column(sa.ForeignKey("item_types.id"), primary_key=True)
    contract_id: Mapped[int] = mapped_column(sa.ForeignKey("contracts.contract_id"), primary_key=True)
    requested: Mapped[bool] = mapped_column(primary_key=True)
    quantity: Mapped[int]

    type: Mapped[ItemType] = relationship()
    contract: Mapped["Contract"] = relationship(back_populates="items")

class Contract(Base):
    __tablename__ = "contracts"

    contract_id: Mapped[int] = mapped_column(primary_key=True)
    contractor_id: Mapped[int] = mapped_column(sa.ForeignKey("contract_entities.id"))
    contracted_to: Mapped[int] = mapped_column(sa.ForeignKey("contract_entities.id"))
    location_id: Mapped[int] = mapped_column(sa.ForeignKey("structures.id"))
    fueller_id: Mapped[int | None] = mapped_column(sa.ForeignKey("contract_entities.id"))
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