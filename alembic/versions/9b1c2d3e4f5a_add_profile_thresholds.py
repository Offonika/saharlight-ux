"""add profile thresholds

Revision ID: 9b1c2d3e4f5a
Revises: 1a2b3c4d5e6f
Create Date: 2025-08-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9b1c2d3e4f5a'
down_revision: Union[str, None] = '1a2b3c4d5e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("profiles", sa.Column("low_threshold", sa.Float(), nullable=True))
    op.add_column("profiles", sa.Column("high_threshold", sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("profiles", "high_threshold")
    op.drop_column("profiles", "low_threshold")
