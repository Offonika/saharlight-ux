from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250908_add_onboarding_metrics_daily"
down_revision: Union[str, Sequence[str], None] = (
    "20250906_move_user_settings_to_profile"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "onboarding_metrics_daily",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("variant", sa.String(), nullable=False),
        sa.Column("step", sa.String(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("date", "variant", "step"),
    )


def downgrade() -> None:
    op.drop_table("onboarding_metrics_daily")
