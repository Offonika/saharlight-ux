from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20250917_user_plan_enum"
down_revision: Union[str, Sequence[str], None] = (
    "20250910_add_onboarding_events_metrics"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

plan_enum = postgresql.ENUM(
    "free",
    "pro",
    "family",
    name="subscription_plan",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        plan_enum.create(bind, checkfirst=True)
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column("plan", type_=plan_enum)
    else:
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column("plan", type_=sa.String())


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("plan", type_=sa.String())
