"""merge heads

Revision ID: 11eb7c3deda6_merge_heads
Revises: 20251002_billing_event_lowercase, 20251002_subscription_plan_values_callable
Create Date: 2025-09-04 19:44:43.266143

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11eb7c3deda6_merge_heads'
down_revision: Union[str, None] = ('20251002_billing_event_lowercase', '20251002_subscription_plan_values_callable')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
