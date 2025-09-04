"""add progress state fields

Revision ID: 20250914_add_progress_state_fields
Revises: 20250913_subscription_status_lowercase
Create Date: 2025-09-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20250914_add_progress_state_fields"
down_revision: Union[str, None] = "20250913_subscription_status_lowercase"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lesson_progress",
        sa.Column(
            "current_step",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "lesson_progress",
        sa.Column(
            "current_question",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("lesson_progress", "current_question")
    op.drop_column("lesson_progress", "current_step")
