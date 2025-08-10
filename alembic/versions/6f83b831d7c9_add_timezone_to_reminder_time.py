"""make reminder time timezone aware"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '6f83b831d7c9'
down_revision: Union[str, None] = 'de2fbeefa646'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('reminders', 'time', type_=sa.TIMESTAMP(timezone=True))


def downgrade() -> None:
    op.alter_column('reminders', 'time', type_=sa.TIMESTAMP(timezone=False))
