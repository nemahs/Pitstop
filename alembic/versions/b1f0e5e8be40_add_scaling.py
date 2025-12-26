"""Add scaling

Revision ID: b1f0e5e8be40
Revises: 9c57cda75e00
Create Date: 2025-11-24 17:11:30.972830

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b1f0e5e8be40'
down_revision: str | None = '9c57cda75e00'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('contract_entities', sa.Column('updated_at', sa.DateTime, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('contract_entities', 'updated_at')
