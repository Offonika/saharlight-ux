from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20250913_lowercase_subscription_status"
down_revision: Union[str, Sequence[str], None] = "20250912_add_lesson_steps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE subscription_status_new AS ENUM ('trial','active','canceled','expired')")
    op.execute(
        "ALTER TABLE subscriptions ALTER COLUMN status TYPE subscription_status_new USING lower(status::text)::subscription_status_new"
    )
    op.execute("DROP TYPE subscription_status")
    op.execute("ALTER TYPE subscription_status_new RENAME TO subscription_status")


def downgrade() -> None:
    op.execute("CREATE TYPE subscription_status_old AS ENUM ('trial','pending','active','canceled','expired')")
    op.execute(
        "ALTER TABLE subscriptions ALTER COLUMN status TYPE subscription_status_old USING status::text::subscription_status_old"
    )
    op.execute("DROP TYPE subscription_status")
    op.execute("ALTER TYPE subscription_status_old RENAME TO subscription_status")
