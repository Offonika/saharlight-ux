"""add composite index for lesson logs"""

from typing import Sequence, Union

from alembic import op

revision: str = "20251009_lesson_logs_user_plan_index"
down_revision: Union[str, Sequence[str], None] = "20251008_recreate_lesson_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_index("ix_lesson_logs_plan_id", table_name="lesson_logs")
    op.drop_index("ix_lesson_logs_user_id", table_name="lesson_logs")
    op.create_index(
        "ix_lesson_logs_user_plan", "lesson_logs", ["user_id", "plan_id"]
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_index("ix_lesson_logs_user_plan", table_name="lesson_logs")
    op.create_index("ix_lesson_logs_user_id", "lesson_logs", ["user_id"])
    op.create_index("ix_lesson_logs_plan_id", "lesson_logs", ["plan_id"])
