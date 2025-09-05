"""add slug to lessons"""

from __future__ import annotations

import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20250918_add_slug_to_lessons"
down_revision: Union[str, Sequence[str], None] = "20250917_profile_not_null_defaults"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

lessons_table = sa.table(
    "lessons",
    sa.column("id", sa.Integer),
    sa.column("title", sa.String),
    sa.column("slug", sa.String),
)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return slug.strip("-") or "lesson"


def upgrade() -> None:
    op.add_column("lessons", sa.Column("slug", sa.String(), nullable=True))
    bind = op.get_bind()
    existing_slugs: set[str] = set()
    rows = list(bind.execute(sa.select(lessons_table.c.id, lessons_table.c.title)))
    for lesson_id, title in rows:
        base = _slugify(title or "lesson")
        slug = base
        counter = 1
        while slug in existing_slugs:
            slug = f"{base}-{counter}"
            counter += 1
        existing_slugs.add(slug)
        bind.execute(
            sa.update(lessons_table)
            .where(lessons_table.c.id == lesson_id)
            .values(slug=slug)
        )
    if bind.dialect.name == "postgresql":
        op.alter_column("lessons", "slug", existing_type=sa.String(), nullable=False)
    op.create_index("ix_lessons_slug", "lessons", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_lessons_slug", table_name="lessons")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_column("lessons", "slug")
    else:
        with op.batch_alter_table("lessons") as batch_op:
            batch_op.drop_column("slug")
