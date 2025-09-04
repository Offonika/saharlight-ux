"""move user settings to profile

Revision ID: 20250906_move_user_settings_to_profile
Revises: 016dca0fbac4_change_description
Create Date: 2025-09-06
"""

from alembic import op
import sqlalchemy as sa


revision = "20250906_move_user_settings_to_profile"
down_revision = "016dca0fbac4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("timezone", sa.String(), nullable=False, server_default="UTC"))
    op.add_column("profiles", sa.Column("timezone_auto", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("profiles", sa.Column("dia", sa.Float(), nullable=False, server_default="4.0"))
    op.add_column("profiles", sa.Column("round_step", sa.Float(), nullable=False, server_default="0.5"))
    op.add_column("profiles", sa.Column("carb_units", sa.String(), nullable=False, server_default="g"))
    op.add_column("profiles", sa.Column("grams_per_xe", sa.Float(), nullable=False, server_default="12.0"))
    op.add_column("profiles", sa.Column("therapy_type", sa.String(), nullable=False, server_default="insulin"))
    op.add_column("profiles", sa.Column("glucose_units", sa.String(), nullable=False, server_default="mmol/L"))
    op.add_column("profiles", sa.Column("insulin_type", sa.String(), nullable=True))
    op.add_column("profiles", sa.Column("prebolus_min", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("profiles", sa.Column("max_bolus", sa.Float(), nullable=False, server_default="10.0"))
    op.add_column("profiles", sa.Column("postmeal_check_min", sa.Integer(), nullable=False, server_default="0"))

    op.execute(
        """
        UPDATE profiles
        SET timezone = u.timezone,
            timezone_auto = u.timezone_auto
        FROM users AS u
        WHERE profiles.telegram_id = u.telegram_id
        """
    )

    op.drop_column("users", "timezone")
    op.drop_column("users", "timezone_auto")

    op.alter_column("profiles", "timezone", server_default=None)
    op.alter_column("profiles", "timezone_auto", server_default=None)
    op.alter_column("profiles", "dia", server_default=None)
    op.alter_column("profiles", "round_step", server_default=None)
    op.alter_column("profiles", "carb_units", server_default=None)
    op.alter_column("profiles", "grams_per_xe", server_default=None)
    op.alter_column("profiles", "therapy_type", server_default=None)
    op.alter_column("profiles", "glucose_units", server_default=None)
    op.alter_column("profiles", "prebolus_min", server_default=None)
    op.alter_column("profiles", "max_bolus", server_default=None)
    op.alter_column("profiles", "postmeal_check_min", server_default=None)


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("timezone_auto", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "users", sa.Column("timezone", sa.String(), nullable=False, server_default="UTC")
    )

    op.execute(
        """
        UPDATE users
        SET timezone = p.timezone,
            timezone_auto = p.timezone_auto
        FROM profiles AS p
        WHERE users.telegram_id = p.telegram_id
        """
    )

    op.drop_column("profiles", "postmeal_check_min")
    op.drop_column("profiles", "max_bolus")
    op.drop_column("profiles", "prebolus_min")
    op.drop_column("profiles", "insulin_type")
    op.drop_column("profiles", "glucose_units")
    op.drop_column("profiles", "therapy_type")
    op.drop_column("profiles", "grams_per_xe")
    op.drop_column("profiles", "carb_units")
    op.drop_column("profiles", "round_step")
    op.drop_column("profiles", "dia")
    op.drop_column("profiles", "timezone_auto")
    op.drop_column("profiles", "timezone")

    op.alter_column("users", "timezone_auto", server_default=None)
    op.alter_column("users", "timezone", server_default=None)
