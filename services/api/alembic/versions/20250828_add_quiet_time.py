"""make quiet_start and quiet_end not nullable"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250828_add_quiet_time"
down_revision: Union[str, None] = "20250824_reminders_kind_minutes_days_mask"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("profiles") as batch_op:
        batch_op.alter_column(
            "quiet_start",
            existing_type=sa.Time(),
            nullable=False,
            server_default=sa.text("'23:00:00'"),
        )
        batch_op.alter_column(
            "quiet_end",
            existing_type=sa.Time(),
            nullable=False,
            server_default=sa.text("'07:00:00'"),
        )


def downgrade() -> None:
    with op.batch_alter_table("profiles") as batch_op:
        batch_op.alter_column(
            "quiet_start",
            existing_type=sa.Time(),
            nullable=True,
            server_default=sa.text("'23:00:00'"),
        )
        batch_op.alter_column(
            "quiet_end",
            existing_type=sa.Time(),
            nullable=True,
            server_default=sa.text("'07:00:00'"),
        )
