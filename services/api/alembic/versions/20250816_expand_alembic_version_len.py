"""Expand alembic_version.version_num to VARCHAR(255)."""

from alembic import op
import sqlalchemy as sa

# NB: новая ревизия вставляется между 20250816 и 20250817
revision = "20250816_expand_alembic_version_len"
down_revision = "20250816_add_org_id_to_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("alembic_version") as batch_op:
        batch_op.alter_column("version_num", type_=sa.String(255))


def downgrade() -> None:
    # осторожно: может не влезть, если в истории уже длинные id
    with op.batch_alter_table("alembic_version") as batch_op:
        batch_op.alter_column("version_num", type_=sa.String(32))
