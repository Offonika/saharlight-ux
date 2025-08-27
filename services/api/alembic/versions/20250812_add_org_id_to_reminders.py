"""add org_id to reminders safely

Revision ID: 20250812_add_org_id_to_reminders
Revises: 02857aa7fc3e
Create Date: 2025-08-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op  # type: ignore[import-not-found]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20250812_add_org_id_to_reminders"
down_revision: Union[str, None] = "02857aa7fc3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = [col["name"] for col in inspector.get_columns("reminders")]
    if "org_id" not in columns:
        op.add_column("reminders", sa.Column("org_id", sa.Integer(), nullable=True))

    indexes = [idx["name"] for idx in inspector.get_indexes("reminders")]
    if "ix_reminders_org_id" not in indexes:
        op.create_index("ix_reminders_org_id", "reminders", ["org_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    indexes = [idx["name"] for idx in inspector.get_indexes("reminders")]
    if "ix_reminders_org_id" in indexes:
        op.drop_index("ix_reminders_org_id", table_name="reminders")

    columns = [col["name"] for col in inspector.get_columns("reminders")]
    if "org_id" in columns:
        op.drop_column("reminders", "org_id")
