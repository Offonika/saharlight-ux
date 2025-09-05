from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250904_billing_log"
down_revision: Union[str, Sequence[str], None] = "20250902_drop_user_timezone"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "billing_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "event",
            sa.Enum(
                "init",
                "checkout_created",
                "webhook_ok",
                "expired",
                "canceled",
                name="billing_event",
            ),
            nullable=False,
        ),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("context", sa.JSON(), nullable=True),
    )
    op.create_index("ix_billing_logs_user_id", "billing_logs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_billing_logs_user_id", table_name="billing_logs")
    op.drop_table("billing_logs")
    op.execute("DROP TYPE billing_event")
