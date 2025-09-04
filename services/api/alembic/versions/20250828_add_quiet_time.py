"""add quiet_start and quiet_end to profiles"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250828_add_quiet_time"
down_revision: Union[str, None] = "20250825_add_quiet_hours_to_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "profiles",
        "quiet_start",
        existing_type=sa.Time(),
        nullable=False,
        server_default=sa.text("'23:00:00'"),
    )
    op.alter_column(
        "profiles",
        "quiet_end",
        existing_type=sa.Time(),
        nullable=False,
        server_default=sa.text("'23:00:00'"),
    )


def downgrade() -> None:
    op.alter_column(
        "profiles",
        "quiet_start",
        existing_type=sa.Time(),
        nullable=True,
        server_default=sa.text("'23:00:00'"),
    )
    op.alter_column(
        "profiles",
        "quiet_end",
        existing_type=sa.Time(),
        nullable=True,
        server_default=sa.text("'23:00:00'"),
    )
