"""add is_enabled to reminders

Revision ID: c0d1e2f3a4b5
Revises: b5a1c2d3e4f6
Create Date: 2025-09-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c0d1e2f3a4b5'
down_revision: Union[str, None] = 'b5a1c2d3e4f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'reminders',
        sa.Column('is_enabled', sa.Boolean(), server_default=sa.true(), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('reminders', 'is_enabled')
