"""change history date and time column types"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250819_change_history_date_time_types"
down_revision: Union[str, None] = "20250818_add_name_fields_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("history_records") as batch:
        batch.alter_column("date", existing_type=sa.String(), type_=sa.Date())
        batch.alter_column("time", existing_type=sa.String(), type_=sa.Time())


def downgrade() -> None:
    with op.batch_alter_table("history_records") as batch:
        batch.alter_column("date", existing_type=sa.Date(), type_=sa.String())
        batch.alter_column("time", existing_type=sa.Time(), type_=sa.String())
