"""add org_id to entries safely

Revision ID: 20250815_add_org_id_to_entries
Revises: 20250814_add_org_id_to_profiles
Create Date: 2025-08-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20250815_add_org_id_to_entries"
down_revision: Union[str, None] = "20250814_add_org_id_to_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = [col["name"] for col in inspector.get_columns("entries")]
    if "org_id" not in columns:
        op.add_column("entries", sa.Column("org_id", sa.Integer(), nullable=True))

    indexes = [idx["name"] for idx in inspector.get_indexes("entries")]
    if "ix_entries_org_id" not in indexes:
        op.create_index("ix_entries_org_id", "entries", ["org_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    indexes = [idx["name"] for idx in inspector.get_indexes("entries")]
    if "ix_entries_org_id" in indexes:
        op.drop_index("ix_entries_org_id", table_name="entries")

    columns = [col["name"] for col in inspector.get_columns("entries")]
    if "org_id" in columns:
        if bind.dialect.name == "postgresql":
            op.drop_column("entries", "org_id")
        else:
            with op.batch_alter_table("entries") as batch_op:
                batch_op.drop_column("org_id")
