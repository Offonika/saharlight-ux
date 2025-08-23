"""change history date and time column types"""

from typing import Sequence, Union

from alembic import op

revision: str = "20250819_change_history_date_time_types"
down_revision: Union[str, None] = "20250818_add_name_fields_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE history_records ALTER COLUMN date TYPE DATE USING date::DATE"
    )
    op.execute(
        "ALTER TABLE history_records ALTER COLUMN time TYPE TIME USING time::TIME"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE history_records ALTER COLUMN date TYPE VARCHAR USING date::TEXT"
    )
    op.execute(
        "ALTER TABLE history_records ALTER COLUMN time TYPE VARCHAR USING time::TEXT"
    )
