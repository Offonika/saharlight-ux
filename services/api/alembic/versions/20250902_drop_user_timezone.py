from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250902_drop_user_timezone"
down_revision: Union[str, Sequence[str], None] = "20250902_reminder_log_telegram_foreign_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "timezone")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("timezone", sa.String(), nullable=False, server_default="UTC"),
    )
    op.alter_column("users", "timezone", server_default=None)
