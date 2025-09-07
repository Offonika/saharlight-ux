"""add assistant_memory table"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20251005_add_assistant_memory"
down_revision: Union[str, Sequence[str], None] = "20251004_lesson_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assistant_memory",
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.telegram_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("turn_count", sa.Integer(), nullable=False),
        sa.Column("last_turn_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index("ix_assistant_memory_user_id", "assistant_memory", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_assistant_memory_user_id", table_name="assistant_memory")
    op.drop_table("assistant_memory")
