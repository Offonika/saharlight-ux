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
    op.alter_column(
        "profiles",
        "timezone",
        existing_type=sa.String(),
        nullable=False,
        server_default="UTC",
    )
    op.alter_column(
        "profiles",
        "timezone_auto",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.true(),
    )
    op.alter_column(
        "profiles",
        "dia",
        existing_type=sa.Float(),
        nullable=False,
        server_default="4.0",
    )
    op.alter_column(
        "profiles",
        "round_step",
        existing_type=sa.Float(),
        nullable=False,
        server_default="0.5",
    )
    op.alter_column(
        "profiles",
        "carb_units",
        existing_type=sa.String(),
        nullable=False,
        server_default="g",
    )
    op.alter_column(
        "profiles",
        "grams_per_xe",
        existing_type=sa.Float(),
        nullable=False,
        server_default="12.0",
    )
    op.alter_column(
        "profiles",
        "therapy_type",
        existing_type=sa.String(),
        nullable=False,
        server_default="insulin",
    )
    op.alter_column(
        "profiles",
        "glucose_units",
        existing_type=sa.String(),
        nullable=False,
        server_default="mmol/L",
    )
    op.alter_column(
        "profiles",
        "prebolus_min",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="0",
    )
    op.alter_column(
        "profiles",
        "max_bolus",
        existing_type=sa.Float(),
        nullable=False,
        server_default="10.0",
    )
    op.alter_column(
        "profiles",
        "postmeal_check_min",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="0",
    )


def downgrade() -> None:
    op.alter_column("profiles", "postmeal_check_min", server_default=None)
    op.alter_column("profiles", "max_bolus", server_default=None)
    op.alter_column("profiles", "prebolus_min", server_default=None)
    op.alter_column("profiles", "glucose_units", server_default=None)
    op.alter_column("profiles", "therapy_type", server_default=None)
    op.alter_column("profiles", "grams_per_xe", server_default=None)
    op.alter_column("profiles", "carb_units", server_default=None)
    op.alter_column("profiles", "round_step", server_default=None)
    op.alter_column("profiles", "dia", server_default=None)
    op.alter_column("profiles", "timezone_auto", server_default=None)
    op.alter_column("profiles", "timezone", server_default=None)

