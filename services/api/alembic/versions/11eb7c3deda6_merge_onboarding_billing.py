"""merge onboarding billing

Revision ID: 11eb7c3deda6_merge_onboarding_billing
Revises: 11eb7c3deda6_merge_heads, 20251003_onboarding_event
Create Date: 2025-10-03 00:00:00.000000

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "11eb7c3deda6_merge_onboarding_billing"
down_revision: Union[str, Sequence[str], None] = (
    "11eb7c3deda6_merge_heads",
    "20251003_onboarding_event",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
