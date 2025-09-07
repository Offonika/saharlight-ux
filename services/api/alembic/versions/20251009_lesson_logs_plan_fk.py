from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20251009_lesson_logs_plan_fk"
down_revision: Union[str, Sequence[str], None] = "3539fae8f7b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "lesson_logs_plan_id_fkey",
        "lesson_logs",
        "learning_plans",
        ["plan_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("lesson_logs_plan_id_fkey", "lesson_logs", type_="foreignkey")
