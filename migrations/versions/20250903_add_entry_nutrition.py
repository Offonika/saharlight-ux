from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250903_add_entry_nutrition"
down_revision: Union[str, Sequence[str], None] = "20250902_drop_user_timezone"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("entries", sa.Column("weight_g", sa.Float(), nullable=True))
    op.add_column("entries", sa.Column("protein_g", sa.Float(), nullable=True))
    op.add_column("entries", sa.Column("fat_g", sa.Float(), nullable=True))
    op.add_column("entries", sa.Column("calories_kcal", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("entries", "calories_kcal")
    op.drop_column("entries", "fat_g")
    op.drop_column("entries", "protein_g")
    op.drop_column("entries", "weight_g")
