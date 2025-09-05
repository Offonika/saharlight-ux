from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20250918_add_learning_unique_constraints"
down_revision: Union[str, Sequence[str], None] = "20250917_profile_not_null_defaults"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_unique_constraint(
            "lesson_steps_lesson_order_key",
            "lesson_steps",
            ["lesson_id", "step_order"],
        )
        op.create_unique_constraint(
            "lesson_progress_user_lesson_key",
            "lesson_progress",
            ["user_id", "lesson_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint(
            "lesson_progress_user_lesson_key",
            table_name="lesson_progress",
            type_="unique",
        )
        op.drop_constraint(
            "lesson_steps_lesson_order_key",
            table_name="lesson_steps",
            type_="unique",
        )
