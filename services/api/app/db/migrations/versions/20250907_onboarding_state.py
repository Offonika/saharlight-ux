"""create onboarding_states table"""

from alembic import op
import sqlalchemy as sa

revision = "20250907_onboarding_state"
down_revision = "20250906_move_user_settings_to_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "onboarding_states",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.telegram_id"), primary_key=True),
        sa.Column("step", sa.String(), nullable=False),
        sa.Column("data_json", sa.JSON(), nullable=True),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), onupdate=sa.func.now()),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("variant", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("onboarding_states")
