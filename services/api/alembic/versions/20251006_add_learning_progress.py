from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20251006_add_learning_progress"
down_revision: Union[str, Sequence[str], None] = (
    "20251005_add_assistant_memory",
    "20251005_add_learning_plans",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learning_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.BigInteger(), sa.ForeignKey("users.telegram_id"), nullable=False
        ),
        sa.Column(
            "plan_id", sa.Integer(), sa.ForeignKey("learning_plans.id"), nullable=False
        ),
        sa.Column(
            "progress_json",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text("'{}'"),
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
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_learning_progress_user_id_plan_id",
        "learning_progress",
        ["user_id", "plan_id"],
    )
    op.create_index(
        "ix_learning_progress_updated_at",
        "learning_progress",
        ["updated_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_learning_progress_updated_at",
        table_name="learning_progress",
        postgresql_if_exists=True,
    )
    op.drop_index(
        "ix_learning_progress_user_id_plan_id",
        table_name="learning_progress",
        postgresql_if_exists=True,
    )
    op.drop_table("learning_progress")
