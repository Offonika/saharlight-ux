"""add quiet_start and quiet_end to profiles"""

from collections.abc import Mapping, Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.engine import Connection


# ID предыдущей и текущей миграции
revision = '20250828_add_quiet_time'
down_revision = '1188e4de1729'
branch_labels = None
depends_on = None


def column_exists(conn: Connection, table_name: str, column_name: str) -> bool:
    insp = inspect(conn)
    columns: Sequence[Mapping[str, object]] = insp.get_columns(table_name)
    return column_name in [col["name"] for col in columns]


def upgrade() -> None:
    bind: Connection = op.get_bind()
    
    if column_exists(bind, "profiles", "quiet_start"):
        op.alter_column(
            "profiles",
            "quiet_start",
            existing_type=sa.Time(),
            nullable=False,
            server_default=sa.text("'23:00:00'"),
        )
    else:
        op.add_column(
            "profiles",
            sa.Column(
                "quiet_start",
                sa.Time(),
                nullable=False,
                server_default=sa.text("'23:00:00'"),
            ),
        )

    if column_exists(bind, "profiles", "quiet_end"):
        op.alter_column(
            "profiles",
            "quiet_end",
            existing_type=sa.Time(),
            nullable=False,
            server_default=sa.text("'07:00:00'"),
        )
    else:
        op.add_column(
            "profiles",
            sa.Column(
                "quiet_end",
                sa.Time(),
                nullable=False,
                server_default=sa.text("'07:00:00'"),
            ),
        )


def downgrade() -> None:
    op.alter_column(
        "profiles",
        "quiet_end",
        existing_type=sa.Time(),
        nullable=True,
        server_default=sa.text("'07:00'"),
    )
    op.alter_column(
        "profiles",
        "quiet_start",
        existing_type=sa.Time(),
        nullable=True,
        server_default=sa.text("'23:00'"),
    )
