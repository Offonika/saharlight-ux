from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250916_reminder_type_kind_enum"
down_revision: Union[str, Sequence[str], None] = (
    "20250915_add_unique_transaction_id_to_subscriptions"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

reminder_type_enum = sa.Enum(
    "sugar",
    "insulin_short",
    "insulin_long",
    "after_meal",
    "meal",
    "sensor_change",
    "injection_site",
    "custom",
    name="reminder_type",
)

schedule_kind_enum = sa.Enum(
    "at_time",
    "every",
    "after_event",
    name="schedule_kind",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        reminder_type_enum.create(bind, checkfirst=True)
        schedule_kind_enum.create(bind, checkfirst=True)
        with op.batch_alter_table("reminders") as batch_op:
            batch_op.alter_column("type", type_=reminder_type_enum)
            batch_op.alter_column("kind", type_=schedule_kind_enum)
    else:
        # SQLite lacks support for adding check constraints via ALTER TABLE.
        # The table already stores plain text values, so no additional
        # constraints are enforced in tests.
        return


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.batch_alter_table("reminders") as batch_op:
            batch_op.alter_column("kind", type_=sa.String())
            batch_op.alter_column("type", type_=sa.String())
        schedule_kind_enum.drop(bind, checkfirst=True)
        reminder_type_enum.drop(bind, checkfirst=True)
    else:
        return
