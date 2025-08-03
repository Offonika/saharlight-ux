"""timezone aware timestamps

Revision ID: 1a2b3c4d5e6f
Revises: de2fbeefa646
Create Date: 2025-08-03 04:19:02.954662

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a2b3c4d5e6f'
down_revision: Union[str, None] = 'de2fbeefa646'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'users',
        'created_at',
        type_=sa.TIMESTAMP(timezone=True),
        existing_type=sa.TIMESTAMP(),
        existing_server_default=sa.text('now()'),
    )

    op.alter_column(
        'entries',
        'event_time',
        type_=sa.TIMESTAMP(timezone=True),
        existing_type=sa.TIMESTAMP(),
        existing_nullable=False,
    )
    op.alter_column(
        'entries',
        'created_at',
        type_=sa.TIMESTAMP(timezone=True),
        existing_type=sa.TIMESTAMP(),
        existing_server_default=sa.text('now()'),
    )
    op.alter_column(
        'entries',
        'updated_at',
        type_=sa.TIMESTAMP(timezone=True),
        existing_type=sa.TIMESTAMP(),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'users',
        'created_at',
        type_=sa.TIMESTAMP(),
        existing_type=sa.TIMESTAMP(timezone=True),
        existing_server_default=sa.text('now()'),
    )

    op.alter_column(
        'entries',
        'event_time',
        type_=sa.TIMESTAMP(),
        existing_type=sa.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )
    op.alter_column(
        'entries',
        'created_at',
        type_=sa.TIMESTAMP(),
        existing_type=sa.TIMESTAMP(timezone=True),
        existing_server_default=sa.text('now()'),
    )
    op.alter_column(
        'entries',
        'updated_at',
        type_=sa.TIMESTAMP(),
        existing_type=sa.TIMESTAMP(timezone=True),
    )
