"""merge heads

Revision ID: 20251001_merge_heads
Revises: 20250919_onboarding_events_user_fk, 20250920_onboarding_state_ondelete_cascade, 20251001_onboarding_metrics_indexes
Create Date: 2025-09-04 17:54:48.210001

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20251001_merge_heads"
down_revision: Union[str, None] = (
    "20250919_onboarding_events_user_fk",
    "20250920_onboarding_state_ondelete_cascade",
    "20251001_onboarding_metrics_indexes",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
