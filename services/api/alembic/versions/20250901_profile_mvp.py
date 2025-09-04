from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20250901_profile_mvp"
down_revision: Union[str, Sequence[str], None] = "016dca0fbac4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_settings",
        sa.Column(
            "telegram_id",
            sa.BigInteger(),
            sa.ForeignKey("users.telegram_id"),
            primary_key=True,
        ),
        sa.Column("icr", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("cf", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("target_bg", sa.Float(), nullable=False, server_default="5.5"),
        sa.Column("low_threshold", sa.Float(), nullable=False, server_default="4.0"),
        sa.Column("high_threshold", sa.Float(), nullable=False, server_default="8.0"),
        sa.Column("quiet_start", sa.Time(), nullable=False, server_default="23:00:00"),
        sa.Column("quiet_end", sa.Time(), nullable=False, server_default="07:00:00"),
        sa.Column(
            "sos_alerts_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.alter_column("user_settings", "icr", server_default=None)
    op.alter_column("user_settings", "cf", server_default=None)
    op.alter_column("user_settings", "target_bg", server_default=None)
    op.alter_column("user_settings", "low_threshold", server_default=None)
    op.alter_column("user_settings", "high_threshold", server_default=None)
    op.alter_column("user_settings", "quiet_start", server_default=None)
    op.alter_column("user_settings", "quiet_end", server_default=None)
    op.alter_column("user_settings", "sos_alerts_enabled", server_default=None)


def downgrade() -> None:
    op.drop_table("user_settings")
