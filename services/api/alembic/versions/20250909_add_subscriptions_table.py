from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20250909_add_subscriptions_table"
down_revision: Union[str, Sequence[str], None] = "20250908_add_onboarding_metrics_daily"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

plan_enum = postgresql.ENUM(
    "free",
    "pro",
    "family",
    name="subscription_plan",
    create_type=False,
)
status_enum = postgresql.ENUM(
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
    inspector = sa.inspect(bind)
    if "subscriptions" in inspector.get_table_names():
        return
    if bind.dialect.name == "postgresql":
        plan_enum.create(bind, checkfirst=True)
        status_enum.create(bind, checkfirst=True)
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
