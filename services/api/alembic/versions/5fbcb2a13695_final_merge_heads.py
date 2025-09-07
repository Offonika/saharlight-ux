"""final merge heads

Revision ID: 5fbcb2a13695
Revises: 6bb9531de3c1, 20251015_merge_heads
Create Date: 2025-09-07 22:14:27.433291

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5fbcb2a13695'
down_revision: Union[str, None] = ('6bb9531de3c1', '20251015_merge_heads')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
