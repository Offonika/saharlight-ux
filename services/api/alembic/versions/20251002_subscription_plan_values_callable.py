"""20251002_subscription_plan_values_callable

Revision ID: 20251002_subscription_plan_values_callable
Revises: 20250904_merge_heads
Create Date: 2025-09-04 19:03:02.753378

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20251002_subscription_plan_values_callable"
down_revision: Union[str, None] = "20250904_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
