"""add indexes for onboarding metrics"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20251001_onboarding_metrics_indexes"
down_revision: Union[str, Sequence[str], None] = (
    "20250816_add_org_id_to_alerts",
    "20250821_add_snooze_minutes_to_reminder_logs",
    "20250904_billing_log",
    "20250911_learning_init",
    "20250915_add_unique_transaction_id_to_subscriptions",
    "20250916_reminder_type_kind_enum",
    "20250917_user_plan_enum",
    "20250918_add_entry_indexes",
    "20250918_add_learning_unique_constraints",
    "20250918_add_slug_to_lessons",
    "20250918_subscriptions_user_status_key",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    indexes_events = {
        idx["name"] for idx in inspector.get_indexes("onboarding_events_metrics")
    }
    if "ix_onboarding_events_metrics_variant_step_created_at" not in indexes_events:
        op.create_index(
            "ix_onboarding_events_metrics_variant_step_created_at",
            "onboarding_events_metrics",
            ["variant", "step", "created_at"],
        )

    indexes_daily = {
        idx["name"] for idx in inspector.get_indexes("onboarding_metrics_daily")
    }
    if "ix_onboarding_metrics_daily_date_variant_step" not in indexes_daily:
        op.create_index(
            "ix_onboarding_metrics_daily_date_variant_step",
            "onboarding_metrics_daily",
            ["date", "variant", "step"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    indexes_daily = {
        idx["name"] for idx in inspector.get_indexes("onboarding_metrics_daily")
    }
    if "ix_onboarding_metrics_daily_date_variant_step" in indexes_daily:
        op.drop_index(
            "ix_onboarding_metrics_daily_date_variant_step",
            table_name="onboarding_metrics_daily",
        )

    indexes_events = {
        idx["name"] for idx in inspector.get_indexes("onboarding_events_metrics")
    }
    if "ix_onboarding_events_metrics_variant_step_created_at" in indexes_events:
        op.drop_index(
            "ix_onboarding_events_metrics_variant_step_created_at",
            table_name="onboarding_events_metrics",
        )
