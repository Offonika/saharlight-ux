from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250917_add_entry_indexes"
down_revision: Union[str, Sequence[str], None] = "20250916_reminder_type_kind_enum"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {idx["name"] for idx in inspector.get_indexes("entries")}
    if "ix_entries_telegram_id" not in indexes:
        op.create_index("ix_entries_telegram_id", "entries", ["telegram_id"])
    if "ix_entries_event_time" not in indexes:
        op.create_index("ix_entries_event_time", "entries", ["event_time"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {idx["name"] for idx in inspector.get_indexes("entries")}
    if "ix_entries_event_time" in indexes:
        op.drop_index("ix_entries_event_time", table_name="entries")
    if "ix_entries_telegram_id" in indexes:
        op.drop_index("ix_entries_telegram_id", table_name="entries")
