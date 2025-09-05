"""add name fields to users"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250818_add_name_fields_to_users"
down_revision: Union[str, None] = "20250817_add_timezone_and_history_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = [col["name"] for col in inspector.get_columns("users")]
    if "first_name" not in columns:
        op.add_column("users", sa.Column("first_name", sa.String(), nullable=True))
    if "last_name" not in columns:
        op.add_column("users", sa.Column("last_name", sa.String(), nullable=True))
    if "username" not in columns:
        op.add_column("users", sa.Column("username", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = [col["name"] for col in inspector.get_columns("users")]
    if bind.dialect.name == "postgresql":
        if "username" in columns:
            op.drop_column("users", "username")
        if "last_name" in columns:
            op.drop_column("users", "last_name")
        if "first_name" in columns:
            op.drop_column("users", "first_name")
    else:
        with op.batch_alter_table("users") as batch_op:
            if "username" in columns:
                batch_op.drop_column("username")
            if "last_name" in columns:
                batch_op.drop_column("last_name")
            if "first_name" in columns:
                batch_op.drop_column("first_name")
