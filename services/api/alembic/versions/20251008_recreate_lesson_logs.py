"""recreate lesson_logs with plan fields"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20251008_recreate_lesson_logs"
down_revision: Union[str, Sequence[str], None] = "20251007_remove_chat_texts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_index("ix_lesson_logs_topic_slug", table_name="lesson_logs")
    op.drop_index("ix_lesson_logs_telegram_id", table_name="lesson_logs")

    op.alter_column(
        "lesson_logs",
        "telegram_id",
        new_column_name="user_id",
        existing_type=sa.BigInteger(),
        existing_nullable=False,
    )
    op.add_column("lesson_logs", sa.Column("plan_id", sa.Integer(), nullable=True))
    op.add_column("lesson_logs", sa.Column("module_idx", sa.Integer(), nullable=True))
    op.add_column("lesson_logs", sa.Column("content", sa.Text(), nullable=True))
    op.drop_column("lesson_logs", "topic_slug")

    op.execute(
        "UPDATE lesson_logs SET module_idx = 0, content = '' WHERE module_idx IS NULL",
    )
    op.alter_column(
        "lesson_logs", "module_idx", existing_type=sa.Integer(), nullable=False
    )
    op.alter_column("lesson_logs", "content", existing_type=sa.Text(), nullable=False)

    op.create_index("ix_lesson_logs_user_id", "lesson_logs", ["user_id"])
    op.create_index("ix_lesson_logs_plan_id", "lesson_logs", ["plan_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_index("ix_lesson_logs_plan_id", table_name="lesson_logs")
    op.drop_index("ix_lesson_logs_user_id", table_name="lesson_logs")

    op.add_column(
        "lesson_logs",
        sa.Column("topic_slug", sa.String(), nullable=True),
    )
    op.alter_column(
        "lesson_logs",
        "user_id",
        new_column_name="telegram_id",
        existing_type=sa.BigInteger(),
        existing_nullable=False,
    )
    op.drop_column("lesson_logs", "plan_id")
    op.drop_column("lesson_logs", "module_idx")
    op.drop_column("lesson_logs", "content")

    op.execute("UPDATE lesson_logs SET topic_slug = '' WHERE topic_slug IS NULL")
    op.alter_column(
        "lesson_logs", "topic_slug", existing_type=sa.String(), nullable=False
    )

    op.create_index("ix_lesson_logs_telegram_id", "lesson_logs", ["telegram_id"])
    op.create_index("ix_lesson_logs_topic_slug", "lesson_logs", ["topic_slug"])
