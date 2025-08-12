"""add org_id to reminders

Revision ID: c3dc6e5961a3
Revises: 02857aa7fc3e
Create Date: 2025-08-12 15:59:18.142298

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3dc6e5961a3'
down_revision: Union[str, None] = '02857aa7fc3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('reminders', sa.Column('org_id', sa.Integer()))


def downgrade() -> None:
    op.drop_column('reminders', 'org_id')
