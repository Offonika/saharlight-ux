"""add timezone and history tables

Revision ID: 20250817_add_timezone_and_history_tables
Revises: 20250816_expand_alembic_version_len
Create Date: 2025-08-17 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20250817_add_timezone_and_history_tables"
down_revision: Union[str, None] = "20250816_expand_alembic_version_len"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "timezones" not in tables:
        op.create_table(
            "timezones",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tz", sa.String(), nullable=False),
        )

    if "history_records" not in tables:
        op.create_table(
            "history_records",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("telegram_id", sa.BigInteger(), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("time", sa.Time(), nullable=False),
            sa.Column("sugar", sa.Float(), nullable=True),
            sa.Column("carbs", sa.Float(), nullable=True),
            sa.Column("bread_units", sa.Float(), nullable=True),
            sa.Column("insulin", sa.Float(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("type", sa.String(), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "history_records" in tables:
        op.drop_table("history_records")

    if "timezones" in tables:
        op.drop_table("timezones")
