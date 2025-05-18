import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ..data.esi.esi import parseRFC7231Date
from .typing import *


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


@dataclass
class ByLocation:
    structure: NamedItem
    contract_count: int = 0
    items: list[Any] = field(default_factory=list)


class ContractDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):  # type: ignore
        return Contract.from_json(obj)


class ItemDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):  # type: ignore
        return ContractItems.from_json(obj)


class ItemStatus(str, Enum):
    OFFERED = "offered"
    REQUESTED = "requested"


@dataclass
class ContractItems:
    item_type: NamedItem
    quantity: int
    status: ItemStatus

    @classmethod
    def from_json(cls, data):
        return cls(
            item_type=NamedItem(id=data["type_id"], name=data["name"]),
            quantity=data["quantity"],
            status=ItemStatus.OFFERED if data["is_included"] else ItemStatus.REQUESTED,
        )


@dataclass
class Contract:
    id: BaseID
    creator: NamedItem
    assignee: NamedItem
    alliance: int | None
    contract_id: ContractID
    description: str
    location: NamedItem
    date_issued: datetime | None
    date_expired: datetime
    status: ContractStatus = ContractStatus.UNKNOWN
    price: float = 0.0
    reward: float = 0.0
    type: ContractType = ContractType.UNKNOWN
    items: list[ContractItems] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def from_json(cls, data: dict[str, Any]):
        return cls(
            id=data["contract_id"],
            creator=NamedItem(id=data["issuer_id"], name=data["issuer_name"]),
            assignee=NamedItem(id=data["assignee_id"], name=data["assignee_name"]),
            contract_id=data["contract_id"],
            alliance=data.get("alliance", None),
            description=data["title"],
            location=NamedItem(id=data["start_location_id"], name=data["location_name"]),
            date_expired=parseRFC7231Date(data["date_expired"]),
            date_issued=None,
            status=ContractStatus(data["status"]),
            price=data["price"],
            reward=data["reward"],
            type=ContractType(data["type"]),
        )

    def to_json(self):
        return json.dumps(self.__dict__)
