from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20251016_lesson_logs_unique_constraint"
down_revision: Union[str, Sequence[str], None] = "5fbcb2a13695"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.create_unique_constraint(
            "uq_lesson_logs_user_plan_module_step_role",
            "lesson_logs",
            ["user_id", "plan_id", "module_idx", "step_idx", "role"],
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.drop_constraint(
            "uq_lesson_logs_user_plan_module_step_role",
            "lesson_logs",
            type_="unique",
        )
