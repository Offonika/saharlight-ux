"""restore assistant_memory summary_text

Revision ID: 20251013_restore_assistant_memory_summary
Revises: 20251012_merge_heads
Create Date: 2025-10-13 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20251013_restore_assistant_memory_summary"
down_revision: Union[str, Sequence[str], None] = "20251012_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assistant_memory",
        sa.Column("summary_text", sa.String(length=1024), nullable=False, server_default=""),
    )
    op.alter_column("assistant_memory", "summary_text", server_default=None)


def downgrade() -> None:
    op.drop_column("assistant_memory", "summary_text")
