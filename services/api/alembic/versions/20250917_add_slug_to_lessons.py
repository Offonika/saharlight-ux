"""add slug to lessons

Revision ID: 20250917_add_slug_to_lessons
Revises: 20250916_reminder_type_kind_enum
Create Date: 2025-09-04 16:35:23.605220

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250917_add_slug_to_lessons'
down_revision: Union[str, None] = '20250916_reminder_type_kind_enum'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("lessons", sa.Column("slug", sa.String(), nullable=False))
    op.create_index(
        "ix_lessons_slug", "lessons", ["slug"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_lessons_slug", table_name="lessons")
    op.drop_column("lessons", "slug")
