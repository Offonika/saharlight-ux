"""add org_id to profiles safely

Revision ID: 20250814_add_org_id_to_profiles
Revises: 20250813_add_org_id_to_users
Create Date: 2025-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20250814_add_org_id_to_profiles"
down_revision: Union[str, None] = "20250813_add_org_id_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = [col["name"] for col in inspector.get_columns("profiles")]
    if "org_id" not in columns:
        op.add_column("profiles", sa.Column("org_id", sa.Integer(), nullable=True))

    indexes = [idx["name"] for idx in inspector.get_indexes("profiles")]
    if "ix_profiles_org_id" not in indexes:
        op.create_index("ix_profiles_org_id", "profiles", ["org_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    indexes = [idx["name"] for idx in inspector.get_indexes("profiles")]
    if "ix_profiles_org_id" in indexes:
        op.drop_index("ix_profiles_org_id", table_name="profiles")

    columns = [col["name"] for col in inspector.get_columns("profiles")]
    if "org_id" in columns:
        if bind.dialect.name == "postgresql":
            op.drop_column("profiles", "org_id")
        else:
            with op.batch_alter_table("profiles") as batch_op:
                batch_op.drop_column("org_id")
