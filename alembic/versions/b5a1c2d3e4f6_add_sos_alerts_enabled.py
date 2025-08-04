"""add sos_alerts_enabled to profiles

Revision ID: b5a1c2d3e4f6
Revises: 6ef15f4d16ef
Create Date: 2025-08-06 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b5a1c2d3e4f6"
down_revision: Union[str, None] = "6ef15f4d16ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "profiles",
        sa.Column(
            "sos_alerts_enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("profiles", "sos_alerts_enabled")

