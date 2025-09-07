"""merge heads

Revision ID: 20251015_merge_heads
Revises: 20251014_user_profile_ondelete_cascade, 20251014_user_role_server_default
Create Date: 2025-09-07 18:55:13.778752
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "20251015_merge_heads"
down_revision: Union[str, None] = (
    "20251014_user_profile_ondelete_cascade",
    "20251014_user_role_server_default",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
