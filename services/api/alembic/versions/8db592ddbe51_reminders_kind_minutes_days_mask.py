"""reminders: kind + minutes + days_mask

Revision ID: 8db592ddbe51
Revises: 20250820_change_reminder_time_type
Create Date: 2025-08-24 20:37:49.023280

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8db592ddbe51'
down_revision: Union[str, None] = '20250820_change_reminder_time_type'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = [col["name"] for col in inspector.get_columns("reminders")]
    if "kind" not in columns:
        op.add_column("reminders", sa.Column("kind", sa.String(), nullable=True))
    if "interval_minutes" not in columns:
        op.add_column(
            "reminders", sa.Column("interval_minutes", sa.Integer(), nullable=True)
        )
    if "minutes_after" not in columns:
        op.add_column(
            "reminders", sa.Column("minutes_after", sa.Integer(), nullable=True)
        )
    if "days_mask" not in columns:
        op.add_column("reminders", sa.Column("days_mask", sa.Integer(), nullable=True))
    if "is_enabled" not in columns:
        op.add_column(
            "reminders",
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        )

    indexes = [idx["name"] for idx in inspector.get_indexes("reminders")]
    if "ix_reminders_owner_enabled" not in indexes:
        op.create_index(
            "ix_reminders_owner_enabled",
            "reminders",
            ["telegram_id", "is_enabled"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    indexes = [idx["name"] for idx in inspector.get_indexes("reminders")]
    if "ix_reminders_owner_enabled" in indexes:
        op.drop_index("ix_reminders_owner_enabled", table_name="reminders")

    columns = [col["name"] for col in inspector.get_columns("reminders")]
    if "is_enabled" in columns:
        op.drop_column("reminders", "is_enabled")
    if "days_mask" in columns:
        op.drop_column("reminders", "days_mask")
    if "minutes_after" in columns:
        op.drop_column("reminders", "minutes_after")
    if "interval_minutes" in columns:
        op.drop_column("reminders", "interval_minutes")
    if "kind" in columns:
        op.drop_column("reminders", "kind")
