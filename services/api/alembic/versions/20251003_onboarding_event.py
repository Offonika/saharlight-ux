from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20251003_onboarding_event"
down_revision: Union[str, Sequence[str], None] = "3539fae8f7b6_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.alter_column("onboarding_events", "event_name", new_column_name="event")
    op.alter_column("onboarding_events", "created_at", new_column_name="ts")
    op.alter_column(
        "onboarding_events",
        "step",
        existing_type=sa.Integer(),
        type_=sa.String(),
        existing_nullable=False,
        nullable=True,
        postgresql_using="step::text",
    )
    op.add_column(
        "onboarding_events",
        sa.Column("meta_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_column("onboarding_events", "meta_json")
    op.alter_column(
        "onboarding_events",
        "step",
        existing_type=sa.String(),
        type_=sa.Integer(),
        existing_nullable=True,
        nullable=False,
        postgresql_using="step::integer",
    )
    op.alter_column("onboarding_events", "ts", new_column_name="created_at")
    op.alter_column("onboarding_events", "event", new_column_name="event_name")
