"""merge heads

Revision ID: 20251012_merge_heads
Revises: 20251011_merge_heads
Create Date: 2025-09-07 15:34:50.033001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251012_merge_heads'
down_revision: Union[str, None] = '20251011_merge_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
