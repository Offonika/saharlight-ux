"""add foreign key constraint to history_records.telegram_id"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20250901_history_record_foreign_key"
down_revision: Union[str, Sequence[str], None] = "20250828_add_quiet_time"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    fks = inspector.get_foreign_keys("history_records")
    has_fk = any(
        fk["referred_table"] == "users" and fk["constrained_columns"] == ["telegram_id"]
        for fk in fks
    )
    if not has_fk:
        op.create_foreign_key(
            "history_records_telegram_id_fkey",
            "history_records",
            "users",
            ["telegram_id"],
            ["telegram_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    fks = [fk["name"] for fk in inspector.get_foreign_keys("history_records")]
    if "history_records_telegram_id_fkey" in fks:
        op.drop_constraint(
            "history_records_telegram_id_fkey", "history_records", type_="foreignkey"
        )
