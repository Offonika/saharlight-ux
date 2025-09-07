"""add learning progress table

Revision ID: 20250818_add_learning_progress
Revises: 20250817_add_timezone_and_history_tables
Create Date: 2025-08-18 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20250818_add_learning_progress"
down_revision: Union[str, None] = "20250817_add_timezone_and_history_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learning_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.telegram_id"), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "learning_progress_user_plan_idx",
        "learning_progress",
        ["user_id", "plan_id"],
    )
    op.create_index(
        "learning_progress_updated_at_idx",
        "learning_progress",
        ["updated_at"],
    )


def downgrade() -> None:
    op.drop_index("learning_progress_updated_at_idx", table_name="learning_progress")
    op.drop_index("learning_progress_user_plan_idx", table_name="learning_progress")
    op.drop_table("learning_progress")
