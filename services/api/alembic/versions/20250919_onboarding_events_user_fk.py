"""add foreign key to onboarding_events.user_id

Revision ID: 20250919_onboarding_events_user_fk
Revises: 20250918_add_entry_indexes
Create Date: 2025-09-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250919_onboarding_events_user_fk"
down_revision: Union[str, Sequence[str], None] = "20250918_add_entry_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        inspector = sa.inspect(bind)
        fks = inspector.get_foreign_keys("onboarding_events")
        has_fk = any(
            fk["referred_table"] == "users" and fk["constrained_columns"] == ["user_id"]
            for fk in fks
        )
        if not has_fk:
            op.create_foreign_key(
                "onboarding_events_user_id_fkey",
                "onboarding_events",
                "users",
                ["user_id"],
                ["telegram_id"],
                ondelete="CASCADE",
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        inspector = sa.inspect(bind)
        fks = [fk["name"] for fk in inspector.get_foreign_keys("onboarding_events")]
        if "onboarding_events_user_id_fkey" in fks:
            op.drop_constraint(
                "onboarding_events_user_id_fkey",
                "onboarding_events",
                type_="foreignkey",
            )
