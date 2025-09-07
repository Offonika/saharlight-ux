"""merge onboarding_event with billing/subscription merge

Revision ID: 6bb9531de3c1
Revises: 11eb7c3deda6, 20251003_onboarding_event
Create Date: 2025-09-06 11:38:49.024711

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6bb9531de3c1'

down_revision = ('11eb7c3deda6_merge_heads', '20251003_onboarding_event')

branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
