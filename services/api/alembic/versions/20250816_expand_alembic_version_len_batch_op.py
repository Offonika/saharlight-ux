"""Expand alembic_version.version_num to VARCHAR(255) on SQLite."""

from alembic import op
import sqlalchemy as sa

revision = "20250816_expand_alembic_version_len_batch_op"
down_revision = "20250816_expand_alembic_version_len"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        return
    with op.batch_alter_table("alembic_version") as batch_op:
        batch_op.alter_column("version_num", type_=sa.String(255))


def downgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        return
    with op.batch_alter_table("alembic_version") as batch_op:
        batch_op.alter_column("version_num", type_=sa.String(32))
