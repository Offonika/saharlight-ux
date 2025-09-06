"""add lesson_logs table

Revision ID: 20250818_add_lesson_logs
Revises: 20250817_add_timezone_and_history_tables
Create Date: 2025-08-18 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250818_add_lesson_logs"
down_revision: Union[str, None] = "20250817_add_timezone_and_history_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lesson_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("topic_slug", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("step_idx", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_lesson_logs_telegram_id", "lesson_logs", ["telegram_id"]
    )
    op.create_index(
        "ix_lesson_logs_topic_slug", "lesson_logs", ["topic_slug"]
    )


def downgrade() -> None:
    op.drop_index("ix_lesson_logs_topic_slug", table_name="lesson_logs")
    op.drop_index("ix_lesson_logs_telegram_id", table_name="lesson_logs")
    op.drop_table("lesson_logs")
