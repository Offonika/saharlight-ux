"""add sos_contact to profiles

Revision ID: 6ef15f4d16ef
Revises: a64429805715
Create Date: 2025-08-04 15:02:52.351955

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6ef15f4d16ef'
down_revision: Union[str, None] = 'a64429805715'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("profiles", sa.Column("sos_contact", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("profiles", "sos_contact")
