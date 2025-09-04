"""learning models init"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20250911_learning_init"
down_revision: Union[str, Sequence[str], None] = (
    "20250910_add_onboarding_events_metrics"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
    )
    op.create_table(
        "quiz_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), nullable=False
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column(
            "options",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
        ),
        sa.Column("correct_option", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_quiz_questions_lesson_id", "quiz_questions", ["lesson_id"], unique=False
    )
    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.telegram_id"),
            nullable=False,
        ),
        sa.Column(
            "lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), nullable=False
        ),
        sa.Column(
            "completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("quiz_score", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_lesson_progress_user_id", "lesson_progress", ["user_id"], unique=False
    )
    op.create_index(
        "ix_lesson_progress_lesson_id", "lesson_progress", ["lesson_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_lesson_progress_lesson_id", table_name="lesson_progress")
    op.drop_index("ix_lesson_progress_user_id", table_name="lesson_progress")
    op.drop_table("lesson_progress")
    op.drop_index("ix_quiz_questions_lesson_id", table_name="quiz_questions")
    op.drop_table("quiz_questions")
    op.drop_table("lessons")
