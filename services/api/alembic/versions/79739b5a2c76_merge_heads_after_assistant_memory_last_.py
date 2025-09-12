"""merge heads after assistant_memory_last_mode

Revision ID: 79739b5a2c76
Revises: 20250909_learning_user_profile, 20251017_add_assistant_memory_last_mode
Create Date: 2025-09-12 16:18:26.718920

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '79739b5a2c76'
down_revision: Union[str, None] = ('20250909_learning_user_profile', '20251017_add_assistant_memory_last_mode')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
