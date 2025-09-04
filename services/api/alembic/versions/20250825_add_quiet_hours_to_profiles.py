"""add quiet hours to profiles

Revision ID: 20250825_add_quiet_hours_to_profiles
Revises: 20250824_reminders_kind_minutes_days_mask
Create Date: 2025-08-25 15:24:16.293648

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250825_add_quiet_hours_to_profiles'
down_revision: Union[str, None] = '20250824_reminders_kind_minutes_days_mask'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = [col["name"] for col in inspector.get_columns("profiles")]
    if "quiet_start" not in columns:
        op.add_column(
            "profiles",
            sa.Column(
                "quiet_start",
                sa.Time(),
                nullable=True,
                server_default=sa.text("'23:00'"),
            ),
        )
    if "quiet_end" not in columns:
        op.add_column(
            "profiles",
            sa.Column(
                "quiet_end",
                sa.Time(),
                nullable=True,
                server_default=sa.text("'07:00'"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = [col["name"] for col in inspector.get_columns("profiles")]
    if "quiet_end" in columns:
        op.drop_column("profiles", "quiet_end")
    if "quiet_start" in columns:
        op.drop_column("profiles", "quiet_start")
