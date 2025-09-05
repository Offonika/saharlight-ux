"""onboarding_states user_id ON DELETE CASCADE"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20250920_onboarding_state_ondelete_cascade"
down_revision: Union[str, Sequence[str], None] = "20250918_subscriptions_user_status_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_constraint(
        "onboarding_states_user_id_fkey",
        "onboarding_states",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "onboarding_states_user_id_fkey",
        "onboarding_states",
        "users",
        ["user_id"],
        ["telegram_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_constraint(
        "onboarding_states_user_id_fkey",
        "onboarding_states",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "onboarding_states_user_id_fkey",
        "onboarding_states",
        "users",
        ["user_id"],
        ["telegram_id"],
    )
