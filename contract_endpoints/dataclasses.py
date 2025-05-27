import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Self, cast

from .typing import *
import database as db


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


class ContractType(str, Enum):
    ITEM_EXCHANGE = "item_exchange"
    AUCTION = "auction"
    COURIER = "courier"
    LOAN = "loan"
    UNKNOWN = "unknown"


@dataclass
class NamedItem:
    name: str
    id: BaseID

    @classmethod
    def from_database(cls, item: db.NamedMixin):
        return cls(
            name=item.name,
            id=BaseID(item.id)
        )

@dataclass
class ByLocation:
    structure: NamedItem
    contract_count: int = 0
    items: list[Any] = field(default_factory=list)

class ItemStatus(str, Enum):
    OFFERED = "offered"
    REQUESTED = "requested"


@dataclass
class ContractItems:
    item_type: NamedItem
    quantity: int
    status: ItemStatus

    @classmethod
    def from_database(cls: type[Self], item: db.ContractItem) -> Self:
        return cls(
            item_type=NamedItem.from_database(item.type),
            quantity=item.quantity,
            status=ItemStatus.REQUESTED if item.requested else ItemStatus.OFFERED
        )

@dataclass
class Contract:
    id: ContractID
    creator: NamedItem
    assignee: NamedItem
    alliance: NamedItem | None
    description: str
    location: NamedItem
    date_issued: datetime | None
    date_expired: datetime | None = None
    status: ContractStatus = ContractStatus.UNKNOWN
    price: float = 0.0
    reward: float = 0.0
    type: ContractType = ContractType.UNKNOWN
    items: list[ContractItems] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_database(cls, contract: db.Contract):
        return cls(
            id=ContractID(BaseID(contract.contract_id)),
            creator=NamedItem.from_database(contract.contractor),
            alliance=NamedItem.from_database(contract.contractor.alliance) if contract.contractor.alliance else None,
            status=cast(ContractStatus, contract.status),
            date_issued=contract.created_on,
            location=NamedItem.from_database(contract.structure),
            description=contract.description if contract.description else "",
            assignee=NamedItem.from_database(contract.assignee),
            date_expired=contract.expires_on,
            items=[ContractItems.from_database(x) for x in contract.items]
        )