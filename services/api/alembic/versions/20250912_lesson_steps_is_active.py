"""add lesson steps and is_active to lessons"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20250912_lesson_steps_is_active"
down_revision: Union[str, Sequence[str], None] = ("20250911_learning_init",)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lessons",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.create_table(
        "lesson_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), nullable=False
        ),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_lesson_steps_lesson_id", "lesson_steps", ["lesson_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_lesson_steps_lesson_id", table_name="lesson_steps")
    op.drop_table("lesson_steps")
    op.drop_column("lessons", "is_active")
