"""Expand alembic_version.version_num to VARCHAR(255)."""

from alembic import op

# NB: новая ревизия вставляется между 20250816 и 20250817
revision = "20250816_expand_alembic_version_len"
down_revision = "20250816_add_org_id_to_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return

    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return

    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(32)")
