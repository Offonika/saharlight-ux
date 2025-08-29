"""add quiet_start and quiet_end to profiles"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# ID предыдущей и текущей миграции
revision = '20250828_add_quiet_time'
down_revision = '1188e4de1729'
branch_labels = None
depends_on = None


def column_exists(conn, table_name, column_name):
    insp = inspect(conn)
    return column_name in [col["name"] for col in insp.get_columns(table_name)]


def upgrade():
    bind = op.get_bind()
    
    if not column_exists(bind, "profiles", "quiet_start"):
        op.add_column(
            "profiles",
            sa.Column("quiet_start", sa.Time(), nullable=False, server_default="23:00:00"),
        )

    if not column_exists(bind, "profiles", "quiet_end"):
        op.add_column(
            "profiles",
            sa.Column("quiet_end", sa.Time(), nullable=False, server_default="07:00:00"),
        )


def downgrade():
    op.drop_column("profiles", "quiet_end")
    op.drop_column("profiles", "quiet_start")
