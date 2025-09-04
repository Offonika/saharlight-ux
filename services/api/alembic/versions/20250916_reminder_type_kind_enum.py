"""reminders: enforce enum values for type and kind"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20250916_reminder_type_kind_enum"
down_revision: Union[str, Sequence[str], None] = (
    "20250915_add_unique_transaction_id_to_subscriptions"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


reminder_type_enum = postgresql.ENUM(
    "sugar",
    "insulin_short",
    "insulin_long",
    "after_meal",
    "meal",
    "sensor_change",
    "injection_site",
    "custom",
    name="reminder_type",
    create_type=False,
)

schedule_kind_enum = postgresql.ENUM(
    "at_time",
    "every",
    "after_event",
    name="schedule_kind",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        reminder_type_enum.create(bind, checkfirst=True)
        schedule_kind_enum.create(bind, checkfirst=True)
        op.execute(
            "ALTER TABLE reminders ALTER COLUMN type TYPE reminder_type USING type::reminder_type"
        )
        op.execute(
            "ALTER TABLE reminders ALTER COLUMN kind TYPE schedule_kind USING kind::schedule_kind"
        )
    else:
        with op.batch_alter_table("reminders") as batch_op:
            batch_op.alter_column(
                "type",
                type_=sa.Enum(
                    "sugar",
                    "insulin_short",
                    "insulin_long",
                    "after_meal",
                    "meal",
                    "sensor_change",
                    "injection_site",
                    "custom",
                    name="reminder_type",
                    native_enum=False,
                    create_constraint=True,
                ),
                existing_type=sa.String(),
                nullable=False,
            )
            batch_op.alter_column(
                "kind",
                type_=sa.Enum(
                    "at_time",
                    "every",
                    "after_event",
                    name="schedule_kind",
                    native_enum=False,
                    create_constraint=True,
                ),
                existing_type=sa.String(),
                nullable=True,
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE reminders ALTER COLUMN type TYPE VARCHAR")
        op.execute("ALTER TABLE reminders ALTER COLUMN kind TYPE VARCHAR")
        schedule_kind_enum.drop(bind, checkfirst=True)
        reminder_type_enum.drop(bind, checkfirst=True)
    else:
        with op.batch_alter_table("reminders") as batch_op:
            batch_op.alter_column(
                "kind", type_=sa.String(), existing_type=sa.String(), nullable=True
            )
            batch_op.alter_column(
                "type", type_=sa.String(), existing_type=sa.String(), nullable=False
            )

