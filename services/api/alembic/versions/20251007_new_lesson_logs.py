"""recreate lesson logs table with plan and module"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20251007_new_lesson_logs"
down_revision: Union[str, Sequence[str], None] = "20251006_add_learning_progress"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_table("lesson_logs")
    op.create_table(
        "lesson_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("module_idx", sa.Integer(), nullable=False),
        sa.Column("step_idx", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_lesson_logs_user_id", "lesson_logs", ["user_id"])
    op.create_index("ix_lesson_logs_plan_id", "lesson_logs", ["plan_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_index("ix_lesson_logs_plan_id", table_name="lesson_logs")
    op.drop_index("ix_lesson_logs_user_id", table_name="lesson_logs")
    op.drop_table("lesson_logs")
