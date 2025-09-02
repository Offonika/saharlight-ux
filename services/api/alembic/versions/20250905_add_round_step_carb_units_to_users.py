from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250905_add_round_step_carb_units_to_users"
down_revision: Union[str, Sequence[str], None] = "20250904_add_dia_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("users")]
    if "round_step" not in columns:
        op.add_column(
            "users",
            sa.Column("round_step", sa.Float(), nullable=False, server_default="0.5"),
        )
        op.alter_column("users", "round_step", server_default=None)
    if "carb_units" not in columns:
        op.add_column(
            "users",
            sa.Column("carb_units", sa.String(), nullable=False, server_default="'g'"),
        )
        op.alter_column("users", "carb_units", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("users")]
    if "round_step" in columns:
        op.drop_column("users", "round_step")
    if "carb_units" in columns:
        op.drop_column("users", "carb_units")
