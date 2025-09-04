"""add onboarding_events_metrics"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20250910_add_onboarding_events_metrics"
down_revision: Union[str, Sequence[str], None] = "20250909_add_subscriptions_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "onboarding_events_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("variant", sa.String(), nullable=False),
        sa.Column("step", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("onboarding_events_metrics")

