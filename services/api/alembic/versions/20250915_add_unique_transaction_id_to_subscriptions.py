from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250915_add_unique_transaction_id_to_subscriptions"
down_revision: Union[str, Sequence[str], None] = "20250914_add_progress_state_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_subscriptions_transaction_id", table_name="subscriptions")
    op.create_index(
        "ix_subscriptions_transaction_id",
        "subscriptions",
        ["transaction_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_subscriptions_transaction_id", table_name="subscriptions")
    op.create_index(
        "ix_subscriptions_transaction_id",
        "subscriptions",
        ["transaction_id"],
        unique=False,
    )
