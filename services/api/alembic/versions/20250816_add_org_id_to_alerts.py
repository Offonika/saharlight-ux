"""add org_id to alerts safely

Revision ID: 20250816_add_org_id_to_alerts
Revises: 20250815_add_org_id_to_entries
Create Date: 2025-08-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20250816_add_org_id_to_alerts"
down_revision: Union[str, None] = "20250815_add_org_id_to_entries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = [col["name"] for col in inspector.get_columns("alerts")]
    if "org_id" not in columns:
        op.add_column("alerts", sa.Column("org_id", sa.Integer(), nullable=True))

    indexes = [idx["name"] for idx in inspector.get_indexes("alerts")]
    if "ix_alerts_org_id" not in indexes:
        op.create_index("ix_alerts_org_id", "alerts", ["org_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    indexes = [idx["name"] for idx in inspector.get_indexes("alerts")]
    if "ix_alerts_org_id" in indexes:
        op.drop_index("ix_alerts_org_id", table_name="alerts")

    columns = [col["name"] for col in inspector.get_columns("alerts")]
    if "org_id" in columns:
        if bind.dialect.name == "postgresql":
            op.drop_column("alerts", "org_id")
        else:
            with op.batch_alter_table("alerts") as batch_op:
                batch_op.drop_column("org_id")
