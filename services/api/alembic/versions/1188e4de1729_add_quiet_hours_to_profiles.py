"""add quiet hours to profiles"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "1188e4de1729"
down_revision: Union[str, None] = "8db592ddbe51"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "profiles",
        sa.Column(
            "quiet_start",
            sa.Time(),
            nullable=True,
            server_default=sa.text("'23:00:00'"),
        ),
    )
    op.add_column(
        "profiles",
        sa.Column(
            "quiet_end",
            sa.Time(),
            nullable=True,
            server_default=sa.text("'07:00:00'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("profiles", "quiet_end")
    op.drop_column("profiles", "quiet_start")
