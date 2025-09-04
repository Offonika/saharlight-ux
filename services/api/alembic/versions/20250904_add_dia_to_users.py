from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250904_add_dia_to_users"
down_revision: Union[str, Sequence[str], None] = "20250904_billing_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("users")]
    if "dia" not in columns:
        op.add_column(
            "users",
            sa.Column("dia", sa.Float(), nullable=False, server_default="4.0"),
        )
        op.alter_column("users", "dia", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("users")]
    if "dia" in columns:
        op.drop_column("users", "dia")
