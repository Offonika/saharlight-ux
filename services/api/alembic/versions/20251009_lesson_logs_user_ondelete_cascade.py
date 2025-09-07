"""lesson_logs.user_id ON DELETE CASCADE"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20251009_lesson_logs_user_ondelete_cascade"
down_revision: Union[str, Sequence[str], None] = "20251008_recreate_lesson_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_constraint("lesson_logs_user_id_fkey", "lesson_logs", type_="foreignkey")
    op.create_foreign_key(
        "lesson_logs_user_id_fkey",
        "lesson_logs",
        "users",
        ["user_id"],
        ["telegram_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_constraint("lesson_logs_user_id_fkey", "lesson_logs", type_="foreignkey")
    op.create_foreign_key(
        "lesson_logs_user_id_fkey",
        "lesson_logs",
        "users",
        ["user_id"],
        ["telegram_id"],
    )
