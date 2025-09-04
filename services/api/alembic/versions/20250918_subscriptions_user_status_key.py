from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250918_subscriptions_user_status_key"
down_revision: Union[str, Sequence[str], None] = (
    "20250916_reminder_type_kind_enum",
    "20250917_user_plan_enum",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = {
        c["name"] for c in inspector.get_unique_constraints("subscriptions")
    }
    if "subscriptions_user_status_key" not in constraints:
        op.create_unique_constraint(
            "subscriptions_user_status_key",
            "subscriptions",
            ["user_id", "status"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = {
        c["name"] for c in inspector.get_unique_constraints("subscriptions")
    }
    if "subscriptions_user_status_key" in constraints:
        op.drop_constraint(
            "subscriptions_user_status_key",
            "subscriptions",
            type_="unique",
        )
