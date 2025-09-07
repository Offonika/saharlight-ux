"""remove content from lesson_logs"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20251008_lesson_logs_no_content"
down_revision: Union[str, Sequence[str], None] = "20251007_assistant_memory_privacy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_column("lesson_logs", "content")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.add_column("lesson_logs", sa.Column("content", sa.Text(), nullable=False))
