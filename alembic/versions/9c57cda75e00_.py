"""empty message

Revision ID: 9c57cda75e00
Revises: 
Create Date: 2025-05-24 11:18:59.790565

"""
from typing import Sequence, Union
from enum import Enum, auto

from alembic import op
import sqlalchemy as sa

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

# revision identifiers, used by Alembic.
revision: str = '9c57cda75e00'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    op.create_table("structures",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("name", sa.String(100), unique=True)
    )

    op.create_table("alliances",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("name", sa.String(100), unique=True)
    )

    op.create_table("item_types",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("name", sa.String(100), unique=True)
    )

    op.create_table("contract_entities",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("name", sa.String(100), unique=True),
        sa.Column("type", sa.Enum(EntityType), nullable=False),
        sa.Column("alliance_id", sa.Integer, sa.ForeignKey("alliances.id"), nullable=True),
    )


    op.create_table("contracts",
        sa.Column("contract_id", sa.BigInteger, primary_key=True),
        sa.Column("contractor_id", sa.BigInteger, sa.ForeignKey("contract_entities.id"), nullable=False),
        sa.Column("contracted_to", sa.BigInteger, nullable=False),
        sa.Column("location_id", sa.BigInteger, sa.ForeignKey("structures.id"), nullable=False),
        sa.Column("fueller_id", sa.BigInteger, sa.ForeignKey("contract_entities.id"), nullable=True),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("created_on", sa.DateTime, nullable=False),
        sa.Column("filled_on", sa.DateTime, nullable=True),
        sa.Column("expires_on", sa.DateTime, nullable=False),
        sa.Column("status", sa.Enum(ContractStatus), default=ContractStatus.UNKNOWN),
    )

    op.create_table("items",
        sa.Column("type_id", sa.Integer, sa.ForeignKey("item_types.id"), primary_key=True),
        sa.Column("contract_id", sa.Integer, sa.ForeignKey("contracts.contract_id"), primary_key=True),
        sa.Column("requested", sa.Boolean, primary_key=True),
        sa.Column("quantity", sa.Integer, nullable=False),
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("items")
    op.drop_table("contracts")
    op.drop_table("item_types")
    op.execute("DROP TYPE contractstatus")
    op.drop_table("contract_entities")
    op.execute("DROP TYPE entitytype")
    op.drop_table("structures")
    op.drop_table("alliances")
