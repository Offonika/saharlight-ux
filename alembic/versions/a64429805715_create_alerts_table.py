"""create alerts table

Revision ID: a64429805715
Revises: 9b1c2d3e4f5a
Create Date: 2025-08-04 14:30:00.760979

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a64429805715'
down_revision: Union[str, None] = '9b1c2d3e4f5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.telegram_id')),
        sa.Column('sugar', sa.Float()),
        sa.Column('type', sa.String()),
        sa.Column('ts', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('resolved', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('alerts')
