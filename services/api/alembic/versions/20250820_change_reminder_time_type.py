"""change reminders time column type to time"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250820_change_reminder_time_type"
down_revision: Union[str, None] = "20250819_change_history_date_time_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("reminders") as batch_op:
        batch_op.alter_column("time", type_=sa.Time())


def downgrade() -> None:
    with op.batch_alter_table("reminders") as batch_op:
        batch_op.alter_column("time", type_=sa.String())
