from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20250913_subscription_status_lowercase"
down_revision: Union[str, Sequence[str], None] = "20250912_add_lesson_steps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

status_enum_new = postgresql.ENUM(
    "trial",
    "active",
    "canceled",
    "expired",
    name="subscription_status_new",
)

status_enum_old = postgresql.ENUM(
    "trial",
    "pending",
    "active",
    "canceled",
    "expired",
    name="subscription_status_old",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        status_enum_new.create(bind, checkfirst=True)
        with op.batch_alter_table("subscriptions") as batch_op:
            batch_op.alter_column(
                "status",
                type_=status_enum_new,
                postgresql_using="lower(status::text)::subscription_status_new",
            )
        op.execute("DROP TYPE subscription_status")
        op.execute("ALTER TYPE subscription_status_new RENAME TO subscription_status")
    else:
        op.alter_column("subscriptions", "status", type_=sa.String())


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        status_enum_old.create(bind, checkfirst=True)
        with op.batch_alter_table("subscriptions") as batch_op:
            batch_op.alter_column(
                "status",
                type_=status_enum_old,
                postgresql_using="status::text::subscription_status_old",
            )
        op.execute("DROP TYPE subscription_status")
        op.execute("ALTER TYPE subscription_status_old RENAME TO subscription_status")
    else:
        op.alter_column("subscriptions", "status", type_=sa.String())
