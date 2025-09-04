from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20251002_billing_event_lowercase"
down_revision: Union[str, Sequence[str], None] = "3539fae8f7b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

billing_event_enum_new = postgresql.ENUM(
    "init",
    "checkout_created",
    "webhook_ok",
    "expired",
    "canceled",
    name="billing_event_new",
)

billing_event_enum_old = postgresql.ENUM(
    "INIT",
    "CHECKOUT_CREATED",
    "WEBHOOK_OK",
    "EXPIRED",
    "CANCELED",
    name="billing_event_old",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        billing_event_enum_new.create(bind, checkfirst=True)
        op.execute(
            "ALTER TABLE billing_logs ALTER COLUMN event TYPE billing_event_new "
            "USING lower(event::text)::billing_event_new"
        )
        op.execute("DROP TYPE billing_event")
        op.execute("ALTER TYPE billing_event_new RENAME TO billing_event")
    else:
        op.alter_column("billing_logs", "event", type_=sa.String())


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        billing_event_enum_old.create(bind, checkfirst=True)
        op.execute(
            "ALTER TABLE billing_logs ALTER COLUMN event TYPE billing_event_old "
            "USING upper(event::text)::billing_event_old"
        )
        op.execute("DROP TYPE billing_event")
        op.execute("ALTER TYPE billing_event_old RENAME TO billing_event")
    else:
        op.alter_column("billing_logs", "event", type_=sa.String())

