"""squashed initial

Revision ID: 20250807_squashed_initial
Revises:
Create Date: 2025-08-07 09:15:17.518654

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20250807_squashed_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


subscription_plan_enum = sa.Enum(
    "free",
    "pro",
    "family",
    name="subscription_plan",
)

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

subscription_status_enum = sa.Enum(
    "trial",
    "active",
    "canceled",
    "expired",
    name="subscription_status",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        subscription_plan_enum.create(bind, checkfirst=True)
        reminder_type_enum.create(bind, checkfirst=True)
        schedule_kind_enum.create(bind, checkfirst=True)
        subscription_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("telegram_id", sa.BigInteger(), primary_key=True),
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=True),
        sa.Column("last_name", sa.String(), nullable=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("onboarding_complete", sa.Boolean(), nullable=True),
        sa.Column("plan", subscription_plan_enum, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.telegram_id"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(), nullable=False, server_default=sa.text("'patient'")),
    )

    op.create_table(
        "profiles",
        sa.Column(
            "telegram_id",
            sa.BigInteger(),
            sa.ForeignKey("users.telegram_id"),
            primary_key=True,
        ),
        sa.Column("icr", sa.Float(), nullable=True),
        sa.Column("cf", sa.Float(), nullable=True),
        sa.Column("target_bg", sa.Float(), nullable=True),
        sa.Column("low_threshold", sa.Float(), nullable=True),
        sa.Column("high_threshold", sa.Float(), nullable=True),
        sa.Column("sos_contact", sa.String(), nullable=True),
        sa.Column("sos_alerts_enabled", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column(
            "quiet_start",
            sa.Time(),
            nullable=False,
            server_default=sa.text("'23:00:00'"),
        ),
        sa.Column(
            "quiet_end",
            sa.Time(),
            nullable=False,
            server_default=sa.text("'07:00:00'"),
        ),
        sa.Column(
            "timezone",
            sa.String(),
            nullable=False,
            server_default=sa.text("'UTC'"),
        ),
        sa.Column(
            "timezone_auto",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "dia",
            sa.Float(),
            nullable=False,
            server_default="4.0",
        ),
        sa.Column(
            "round_step",
            sa.Float(),
            nullable=False,
            server_default="0.5",
        ),
        sa.Column(
            "carb_units",
            sa.String(),
            nullable=False,
            server_default=sa.text("'g'"),
        ),
        sa.Column(
            "grams_per_xe",
            sa.Float(),
            nullable=False,
            server_default="12.0",
        ),
        sa.Column(
            "therapy_type",
            sa.String(),
            nullable=False,
            server_default=sa.text("'insulin'"),
        ),
        sa.Column(
            "glucose_units",
            sa.String(),
            nullable=False,
            server_default=sa.text("'mmol/L'"),
        ),
        sa.Column("insulin_type", sa.String(), nullable=True),
        sa.Column(
            "prebolus_min",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "max_bolus",
            sa.Float(),
            nullable=False,
            server_default="10.0",
        ),
        sa.Column(
            "postmeal_check_min",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("org_id", sa.Integer(), nullable=True),
    )

    op.create_table(
        "entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "telegram_id",
            sa.BigInteger(),
            sa.ForeignKey("users.telegram_id"),
            nullable=True,
        ),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column(
            "event_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("photo_path", sa.String(), nullable=True),
        sa.Column("carbs_g", sa.Float(), nullable=True),
        sa.Column("xe", sa.Float(), nullable=True),
        sa.Column("weight_g", sa.Float(), nullable=True),
        sa.Column("protein_g", sa.Float(), nullable=True),
        sa.Column("fat_g", sa.Float(), nullable=True),
        sa.Column("calories_kcal", sa.Float(), nullable=True),
        sa.Column("sugar_before", sa.Float(), nullable=True),
        sa.Column("dose", sa.Float(), nullable=True),
        sa.Column("gpt_summary", sa.Text(), nullable=True),
    )
    op.create_index("ix_entries_telegram_id", "entries", ["telegram_id"])
    op.create_index("ix_entries_event_time", "entries", ["event_time"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.telegram_id"),
            nullable=True,
        ),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column("sugar", sa.Float(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column(
            "ts",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("resolved", sa.Boolean(), nullable=True),
    )

    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "telegram_id",
            sa.BigInteger(),
            sa.ForeignKey("users.telegram_id"),
            nullable=True,
        ),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column("type", reminder_type_enum, nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("kind", schedule_kind_enum, nullable=True),
        sa.Column("time", sa.Time(), nullable=True),
        sa.Column("interval_hours", sa.Integer(), nullable=True),
        sa.Column("interval_minutes", sa.Integer(), nullable=True),
        sa.Column("minutes_after", sa.Integer(), nullable=True),
        sa.Column("days_mask", sa.Integer(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "reminder_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "reminder_id",
            sa.Integer(),
            sa.ForeignKey("reminders.id"),
            nullable=True,
        ),
        sa.Column(
            "telegram_id",
            sa.BigInteger(),
            sa.ForeignKey("users.telegram_id"),
            nullable=True,
        ),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(), nullable=True),
        sa.Column("snooze_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "event_time",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_reminder_logs_telegram_id", "reminder_logs", ["telegram_id"])

    op.create_table(
        "timezones",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            sqlite_on_conflict_primary_key="REPLACE",
        ),
        sa.Column("tz", sa.String(), nullable=False),
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
        sa.Column("plan", subscription_plan_enum, nullable=False),
        sa.Column("status", subscription_status_enum, nullable=False),
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
        sa.UniqueConstraint("user_id", "status", name="subscriptions_user_status_key"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index(
        "ix_subscriptions_transaction_id",
        "subscriptions",
        ["transaction_id"],
        unique=True,
    )

    op.create_table(
        "history_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "telegram_id",
            sa.BigInteger(),
            sa.ForeignKey("users.telegram_id"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("time", sa.Time(), nullable=False),
        sa.Column("sugar", sa.Float(), nullable=True),
        sa.Column("carbs", sa.Float(), nullable=True),
        sa.Column("bread_units", sa.Float(), nullable=True),
        sa.Column("insulin", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
    )
    op.create_index("ix_history_records_telegram_id", "history_records", ["telegram_id"])


def downgrade() -> None:
    op.drop_index("ix_history_records_telegram_id", table_name="history_records")
    op.drop_table("history_records")

    op.drop_index("ix_subscriptions_transaction_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_table("timezones")

    op.drop_index("ix_reminder_logs_telegram_id", table_name="reminder_logs")
    op.drop_table("reminder_logs")

    op.drop_table("reminders")
    op.drop_table("alerts")

    op.drop_index("ix_entries_event_time", table_name="entries")
    op.drop_index("ix_entries_telegram_id", table_name="entries")
    op.drop_table("entries")

    op.drop_table("profiles")
    op.drop_table("user_roles")
    op.drop_table("users")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        subscription_status_enum.drop(bind, checkfirst=True)
        schedule_kind_enum.drop(bind, checkfirst=True)
        reminder_type_enum.drop(bind, checkfirst=True)
        subscription_plan_enum.drop(bind, checkfirst=True)

