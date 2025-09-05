"""add foreign key to reminder_logs.telegram_id"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20250902_reminder_log_telegram_foreign_key"
down_revision: Union[str, Sequence[str], None] = "20250901_history_record_foreign_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    op.execute(
        sa.text(
            """
            UPDATE reminder_logs
            SET telegram_id = NULL
            WHERE telegram_id IS NOT NULL
              AND telegram_id NOT IN (SELECT telegram_id FROM users)
            """
        )
    )

    indexes = [idx["name"] for idx in inspector.get_indexes("reminder_logs")]
    if "ix_reminder_logs_telegram_id" not in indexes:
        op.create_index(
            "ix_reminder_logs_telegram_id",
            "reminder_logs",
            ["telegram_id"],
        )

    fks = inspector.get_foreign_keys("reminder_logs")
    has_fk = any(
        fk["referred_table"] == "users" and fk["constrained_columns"] == ["telegram_id"]
        for fk in fks
    )
    if not has_fk:
        op.create_foreign_key(
            "reminder_logs_telegram_id_fkey",
            "reminder_logs",
            "users",
            ["telegram_id"],
            ["telegram_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    fks = [fk["name"] for fk in inspector.get_foreign_keys("reminder_logs")]
    if "reminder_logs_telegram_id_fkey" in fks:
        op.drop_constraint(
            "reminder_logs_telegram_id_fkey",
            "reminder_logs",
            type_="foreignkey",
        )

    indexes = [idx["name"] for idx in inspector.get_indexes("reminder_logs")]
    if "ix_reminder_logs_telegram_id" in indexes:
        op.drop_index("ix_reminder_logs_telegram_id", table_name="reminder_logs")
