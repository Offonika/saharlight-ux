
"""create onboarding_events table"""

from alembic import op
import sqlalchemy as sa

revision = "20250907_onboarding_events"
down_revision = "20250906_move_user_settings_to_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "onboarding_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.telegram_id"), nullable=False),
        sa.Column("event_name", sa.String(), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("variant", sa.String(), nullable=True),
        sa.Column(
            "ts",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("onboarding_events")
