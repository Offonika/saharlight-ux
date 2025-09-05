"""add snooze_minutes to reminder_logs"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250821_add_snooze_minutes_to_reminder_logs"
down_revision: Union[str, None] = "20250820_change_reminder_time_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("reminder_logs")]
    if "snooze_minutes" not in columns:
        op.add_column(
            "reminder_logs",
            sa.Column("snooze_minutes", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("reminder_logs")]
    if "snooze_minutes" in columns:
        if bind.dialect.name == "postgresql":
            op.drop_column("reminder_logs", "snooze_minutes")
        else:
            with op.batch_alter_table("reminder_logs") as batch_op:
                batch_op.drop_column("snooze_minutes")
