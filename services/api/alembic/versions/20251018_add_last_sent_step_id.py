"""add last_sent_step_id to learning_progress"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251018_add_last_sent_step_id"
down_revision: Union[str, None] = "20251017_add_assistant_memory_last_mode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    progress = sa.table(
        "learning_progress",
        sa.column("id", sa.Integer),
        sa.column("progress_json", sa.JSON()),
    )
    rows = bind.execute(sa.select(progress.c.id, progress.c.progress_json)).fetchall()
    for row in rows:
        data = dict(row.progress_json or {})
        if "last_sent_step_id" not in data:
            data["last_sent_step_id"] = None
            bind.execute(
                sa.update(progress)
                .where(progress.c.id == row.id)
                .values(progress_json=data)
            )


def downgrade() -> None:
    bind = op.get_bind()
    progress = sa.table(
        "learning_progress",
        sa.column("id", sa.Integer),
        sa.column("progress_json", sa.JSON()),
    )
    rows = bind.execute(sa.select(progress.c.id, progress.c.progress_json)).fetchall()
    for row in rows:
        data = dict(row.progress_json or {})
        if "last_sent_step_id" in data:
            data.pop("last_sent_step_id", None)
            bind.execute(
                sa.update(progress)
                .where(progress.c.id == row.id)
                .values(progress_json=data)
            )
