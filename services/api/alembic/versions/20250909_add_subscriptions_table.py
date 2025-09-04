from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250909_add_subscriptions_table"
down_revision: Union[str, Sequence[str], None] = (
    "20250907_onboarding_events",
    "20250908_add_onboarding_metrics_daily",
    "20250907_onboarding_state",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

plan_enum = sa.Enum(
    "free",
    "pro",
    "family",
    name="subscription_plan",
    create_type=False,
)
status_enum = sa.Enum(
    "trial",
    "pending",
    "active",
    "canceled",
    "expired",
    name="subscription_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = 'subscription_plan'
                ) THEN
                    CREATE TYPE subscription_plan AS ENUM ('free', 'pro', 'family');
                END IF;
            END $$;
            """
        )
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = 'subscription_status'
                ) THEN
                    CREATE TYPE subscription_status AS ENUM (
                        'trial', 'pending', 'active', 'canceled', 'expired'
                    );
                END IF;
            END $$;
            """
        )
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.telegram_id"),
            nullable=False,
        ),
        sa.Column("plan", plan_enum, nullable=False),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("transaction_id", sa.String(), nullable=False),
        sa.Column(
            "start_date",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("end_date", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index(
        "ix_subscriptions_transaction_id", "subscriptions", ["transaction_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_subscriptions_transaction_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        status_enum.drop(bind, checkfirst=True)
        plan_enum.drop(bind, checkfirst=True)
