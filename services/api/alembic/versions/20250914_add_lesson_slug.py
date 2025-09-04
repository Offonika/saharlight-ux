"""add lesson slug"""

from __future__ import annotations

import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250914_add_lesson_slug"
down_revision: Union[str, Sequence[str], None] = (
    "20250913_subscription_status_lowercase"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("lessons", sa.Column("slug", sa.String(), nullable=True))
    lesson_table = sa.table(
        "lessons",
        sa.column("id", sa.Integer()),
        sa.column("title", sa.String()),
        sa.column("slug", sa.String()),
    )
    conn = op.get_bind()
    rows = conn.execute(sa.select(lesson_table.c.id, lesson_table.c.title)).fetchall()
    for row in rows:
        slug = re.sub(r"[^a-z0-9]+", "-", row.title.lower()).strip("-")
        conn.execute(
            sa.update(lesson_table).where(lesson_table.c.id == row.id).values(slug=slug)
        )
    op.alter_column("lessons", "slug", nullable=False)
    op.create_index("ix_lessons_slug", "lessons", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_lessons_slug", table_name="lessons")
    op.drop_column("lessons", "slug")
