"""profile settings columns not null with defaults

Revision ID: 20250917_profile_not_null_defaults
Revises: 20250916_reminder_type_kind_enum
Create Date: 2025-09-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20250917_profile_not_null_defaults"
down_revision = "20250916_reminder_type_kind_enum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("profiles") as batch_op:
        batch_op.alter_column(
            "timezone",
            existing_type=sa.String(),
            nullable=False,
            server_default="UTC",
        )
        batch_op.alter_column(
            "timezone_auto",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        )
        batch_op.alter_column(
            "dia",
            existing_type=sa.Float(),
            nullable=False,
            server_default="4.0",
        )
        batch_op.alter_column(
            "round_step",
            existing_type=sa.Float(),
            nullable=False,
            server_default="0.5",
        )
        batch_op.alter_column(
            "carb_units",
            existing_type=sa.String(),
            nullable=False,
            server_default="g",
        )
        batch_op.alter_column(
            "grams_per_xe",
            existing_type=sa.Float(),
            nullable=False,
            server_default="12.0",
        )
        batch_op.alter_column(
            "therapy_type",
            existing_type=sa.String(),
            nullable=False,
            server_default="insulin",
        )
        batch_op.alter_column(
            "glucose_units",
            existing_type=sa.String(),
            nullable=False,
            server_default="mmol/L",
        )
        batch_op.alter_column(
            "prebolus_min",
            existing_type=sa.Integer(),
            nullable=False,
            server_default="0",
        )
        batch_op.alter_column(
            "max_bolus",
            existing_type=sa.Float(),
            nullable=False,
            server_default="10.0",
        )
        batch_op.alter_column(
            "postmeal_check_min",
            existing_type=sa.Integer(),
            nullable=False,
            server_default="0",
        )


def downgrade() -> None:
    with op.batch_alter_table("profiles") as batch_op:
        batch_op.alter_column("postmeal_check_min", server_default=None)
        batch_op.alter_column("max_bolus", server_default=None)
        batch_op.alter_column("prebolus_min", server_default=None)
        batch_op.alter_column("glucose_units", server_default=None)
        batch_op.alter_column("therapy_type", server_default=None)
        batch_op.alter_column("grams_per_xe", server_default=None)
        batch_op.alter_column("carb_units", server_default=None)
        batch_op.alter_column("round_step", server_default=None)
        batch_op.alter_column("dia", server_default=None)
        batch_op.alter_column("timezone_auto", server_default=None)
        batch_op.alter_column("timezone", server_default=None)

