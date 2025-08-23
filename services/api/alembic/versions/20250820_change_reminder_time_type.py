"""change reminders time column type to time"""

from typing import Sequence, Union

from alembic import op

revision: str = "20250820_change_reminder_time_type"
down_revision: Union[str, None] = "20250819_change_history_date_time_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE reminders ALTER COLUMN time TYPE TIME USING time::TIME"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE reminders ALTER COLUMN time TYPE VARCHAR USING time::TEXT"
    )
