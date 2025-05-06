"""add event_time

Revision ID: de2fbeefa646
Revises: 
Create Date: 2025-05-05 15:35:56.537908
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'de2fbeefa646'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем новое поле с дефолтным значением
    op.add_column(
        'entries',
        sa.Column(
            'event_time',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("'2025-01-01 00:00:00'")
        )
    )
    op.add_column('entries', sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True))
    op.add_column('entries', sa.Column('updated_at', sa.TIMESTAMP(), nullable=True))
    op.drop_column('entries', 'timestamp')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('entries', sa.Column('timestamp', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=True))
    op.drop_column('entries', 'updated_at')
    op.drop_column('entries', 'created_at')
    op.drop_column('entries', 'event_time')
