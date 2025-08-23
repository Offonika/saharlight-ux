"""Change reminders.time to TIME type"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250819_change_reminder_time_column_type"
down_revision: Union[str, None] = "20250818_add_name_fields_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("reminders")]
    if "time" in columns:
        op.alter_column(
            "reminders",
            "time",
            existing_type=sa.String(),
            type_=sa.Time(),
            postgresql_using="time::time",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("reminders")]
    if "time" in columns:
        op.alter_column(
            "reminders",
            "time",
            existing_type=sa.Time(),
            type_=sa.String(),
            postgresql_using="time::text",
        )
