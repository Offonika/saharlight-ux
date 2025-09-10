"""lesson_logs unique step role"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20251016_lesson_logs_unique_step_role"
down_revision: Union[str, None] = "5fbcb2a13695"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_lesson_logs_user_plan_module_step_role",
        "lesson_logs",
        ["user_id", "plan_id", "module_idx", "step_idx", "role"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_lesson_logs_user_plan_module_step_role",
        "lesson_logs",
        type_="unique",
    )
