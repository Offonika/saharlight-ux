"""add quiet_start and quiet_end to profiles"""

from collections.abc import Mapping, Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.engine import Connection


# ID предыдущей и текущей миграции
revision = "20250828_add_quiet_time_to_profiles"
down_revision = "20250825_add_quiet_hours_to_profiles"
branch_labels = None
depends_on = None


def column_exists(conn: Connection, table_name: str, column_name: str) -> bool:
    insp = inspect(conn)
    columns: Sequence[Mapping[str, object]] = insp.get_columns(table_name)
    return column_name in [col["name"] for col in columns]


def upgrade() -> None:
    bind: Connection = op.get_bind()

    if not column_exists(bind, "profiles", "quiet_start"):
        op.add_column(
            "profiles",
            sa.Column(
                "quiet_start", sa.Time(), nullable=False, server_default="23:00:00"
            ),
        )

    if not column_exists(bind, "profiles", "quiet_end"):
        op.add_column(
            "profiles",
            sa.Column(
                "quiet_end", sa.Time(), nullable=False, server_default="07:00:00"
            ),
        )


def downgrade() -> None:
    op.drop_column("profiles", "quiet_end")
    op.drop_column("profiles", "quiet_start")
