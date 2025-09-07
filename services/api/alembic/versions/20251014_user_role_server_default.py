"""user role server default

Revision ID: 20251014_user_role_server_default
Revises: 20251013_restore_assistant_memory_summary
Create Date: 2025-09-07 18:14:13.122339

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20251014_user_role_server_default"
down_revision: Union[str, None] = "20251013_restore_assistant_memory_summary"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.alter_column(
        "user_roles",
        "role",
        existing_type=sa.String(),
        server_default=sa.text("'patient'"),
    )
    op.execute(sa.text("UPDATE user_roles SET role='patient'"))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.alter_column("user_roles", "role", server_default=None)
