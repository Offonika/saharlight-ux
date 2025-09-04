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
        op.execute(
            "ALTER TABLE reminders ALTER COLUMN type TYPE reminder_type USING type::text::reminder_type"
        )
        op.execute(
            "ALTER TABLE reminders ALTER COLUMN kind TYPE schedule_kind USING kind::text::schedule_kind"
        )
    else:
        inspector = sa.inspect(bind)
        constraints = {c["name"] for c in inspector.get_check_constraints("reminders")}
        if "reminders_type_check" not in constraints:
            op.create_check_constraint(
                "reminders_type_check",
                "reminders",
                "type IN ('sugar','insulin_short','insulin_long','after_meal','meal','sensor_change','injection_site','custom')",
            )
        if "reminders_kind_check" not in constraints:
            op.create_check_constraint(
                "reminders_kind_check",
                "reminders",
                "(kind IS NULL) OR kind IN ('at_time','every','after_event')",
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE reminders ALTER COLUMN kind TYPE VARCHAR USING kind::text"
        )
        op.execute(
            "ALTER TABLE reminders ALTER COLUMN type TYPE VARCHAR USING type::text"
        )
        schedule_kind_enum.drop(bind, checkfirst=True)
        reminder_type_enum.drop(bind, checkfirst=True)
    else:
        inspector = sa.inspect(bind)
        constraints = {c["name"] for c in inspector.get_check_constraints("reminders")}
        if "reminders_kind_check" in constraints:
            op.drop_constraint("reminders_kind_check", "reminders", type_="check")
        if "reminders_type_check" in constraints:
            op.drop_constraint("reminders_type_check", "reminders", type_="check")
