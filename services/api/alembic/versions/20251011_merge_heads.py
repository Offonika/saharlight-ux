"""merge heads

Revision ID: 20251011_merge_heads
Revises: 11eb7c3deda6_merge_heads, 20251010_lesson_logs_user_plan_index
Create Date: 2025-09-07 15:17:50.994294

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20251011_merge_heads"
down_revision: Union[str, None] = (
    "11eb7c3deda6_merge_heads",
    "20251010_lesson_logs_user_plan_index",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
