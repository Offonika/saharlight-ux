"""update lesson logs schema

Revision ID: 20251007_update_lesson_logs_table
Revises: 20251006_add_learning_progress
Create Date: 2025-10-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20251007_update_lesson_logs_table"
down_revision: Union[str, Sequence[str], None] = "20251006_add_learning_progress"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_index("ix_lesson_logs_topic_slug", table_name="lesson_logs")
    op.drop_index("ix_lesson_logs_telegram_id", table_name="lesson_logs")
    op.alter_column("lesson_logs", "telegram_id", new_column_name="user_id")
    op.drop_column("lesson_logs", "topic_slug")
    op.add_column(
        "lesson_logs",
        sa.Column(
            "plan_id", sa.Integer(), sa.ForeignKey("learning_plans.id"), nullable=False
        ),
    )
    op.add_column(
        "lesson_logs",
        sa.Column(
            "module_idx", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
    )
    op.create_index(
        "ix_lesson_logs_user_id_plan_id",
        "lesson_logs",
        ["user_id", "plan_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_index("ix_lesson_logs_user_id_plan_id", table_name="lesson_logs")
    op.drop_column("lesson_logs", "module_idx")
    op.drop_column("lesson_logs", "plan_id")
    op.add_column(
        "lesson_logs",
        sa.Column("topic_slug", sa.String(), nullable=False),
    )
    op.alter_column("lesson_logs", "user_id", new_column_name="telegram_id")
    op.create_index("ix_lesson_logs_telegram_id", "lesson_logs", ["telegram_id"])
    op.create_index("ix_lesson_logs_topic_slug", "lesson_logs", ["topic_slug"])
