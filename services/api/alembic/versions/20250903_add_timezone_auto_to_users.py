from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250903_add_timezone_auto_to_users"
down_revision: Union[str, Sequence[str], None] = "20250902_reminder_log_telegram_foreign_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("users")]
    if "timezone_auto" not in columns:
        op.add_column(
            "users",
            sa.Column("timezone_auto", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("users")]
    if "timezone_auto" in columns:
        if bind.dialect.name == "postgresql":
            op.drop_column("users", "timezone_auto")
        else:
            with op.batch_alter_table("users") as batch_op:
                batch_op.drop_column("timezone_auto")
