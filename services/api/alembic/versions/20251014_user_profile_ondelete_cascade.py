"""user_roles.user_id and profiles.telegram_id ON DELETE CASCADE"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20251014_user_profile_ondelete_cascade"
down_revision: Union[str, Sequence[str], None] = (
    "20251013_restore_assistant_memory_summary"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_constraint(
        "user_roles_user_id_fkey",
        "user_roles",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "user_roles_user_id_fkey",
        "user_roles",
        "users",
        ["user_id"],
        ["telegram_id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "profiles_telegram_id_fkey",
        "profiles",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "profiles_telegram_id_fkey",
        "profiles",
        "users",
        ["telegram_id"],
        ["telegram_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_constraint(
        "user_roles_user_id_fkey",
        "user_roles",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "user_roles_user_id_fkey",
        "user_roles",
        "users",
        ["user_id"],
        ["telegram_id"],
    )
    op.drop_constraint(
        "profiles_telegram_id_fkey",
        "profiles",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "profiles_telegram_id_fkey",
        "profiles",
        "users",
        ["telegram_id"],
        ["telegram_id"],
    )
