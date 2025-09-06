from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20251005_add_pending_subscription_status"
down_revision: Union[str, Sequence[str], None] = "20251004_lesson_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TYPE subscription_status ADD VALUE IF NOT EXISTS 'pending'"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        status_enum = postgresql.ENUM(
            "trial",
            "active",
            "canceled",
            "expired",
            name="subscription_status_new",
        )
        status_enum.create(bind, checkfirst=True)
        with op.batch_alter_table("subscriptions") as batch_op:
            batch_op.alter_column(
                "status",
                type_=status_enum,
                postgresql_using=(
                    "CASE WHEN status='pending' THEN 'canceled'::subscription_status_new "
                    "ELSE status::text::subscription_status_new END"
                ),
            )
        op.execute("DROP TYPE subscription_status")
        op.execute("ALTER TYPE subscription_status_new RENAME TO subscription_status")
