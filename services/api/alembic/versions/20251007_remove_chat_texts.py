"""remove chat text columns

Revision ID: 20251007_remove_chat_texts
Revises: 20251006_add_learning_progress
Create Date: 2025-10-07 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20251007_remove_chat_texts"
down_revision: Union[str, Sequence[str], None] = "20251006_add_learning_progress"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.drop_column("assistant_memory", "summary_text")
    op.drop_column("lesson_logs", "content")


def downgrade() -> None:
    op.add_column("lesson_logs", sa.Column("content", sa.Text(), nullable=False))
    op.add_column("assistant_memory", sa.Column("summary_text", sa.Text(), nullable=False))
