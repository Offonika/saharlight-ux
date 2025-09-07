"""remove summary_text add profile_url"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20251007_assistant_memory_privacy"
down_revision: Union[str, Sequence[str], None] = "20251006_add_learning_progress"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("assistant_memory", "summary_text")
    op.add_column("assistant_memory", sa.Column("profile_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("assistant_memory", "profile_url")
    op.add_column("assistant_memory", sa.Column("summary_text", sa.Text(), nullable=False))
