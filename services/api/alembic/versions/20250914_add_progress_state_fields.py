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
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_column("lesson_progress", "current_question")
        op.drop_column("lesson_progress", "current_step")
    else:
        with op.batch_alter_table("lesson_progress") as batch_op:
            batch_op.drop_column("current_question")
            batch_op.drop_column("current_step")
