"""add assistant_memory last_mode"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20251017_add_assistant_memory_last_mode"
down_revision: Union[str, None] = "20251016_lesson_logs_unique_step_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("assistant_memory") as batch_op:
            batch_op.add_column(
                sa.Column("last_mode", sa.String(length=16), nullable=True)
            )
    else:
        op.add_column(
            "assistant_memory",
            sa.Column("last_mode", sa.String(length=16), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("assistant_memory") as batch_op:
            batch_op.drop_column("last_mode")
    else:
        op.drop_column("assistant_memory", "last_mode")
