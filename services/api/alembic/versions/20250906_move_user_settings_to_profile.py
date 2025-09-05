"""move user settings to profile

Revision ID: 20250906_move_user_settings_to_profile
Revises: ("20250904_billing_log", "20250904_change_description")
Create Date: 2025-09-06
"""

from alembic import op
import sqlalchemy as sa


revision = "20250906_move_user_settings_to_profile"
down_revision = ("20250904_billing_log", "20250904_change_description")
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    profile_columns = {
        col["name"] for col in inspector.get_columns("profiles")
    }
    user_columns = {col["name"] for col in inspector.get_columns("users")}

    if "timezone" not in profile_columns:
        op.add_column(
            "profiles",
            sa.Column("timezone", sa.String(), nullable=False, server_default="UTC"),
        )
    if "timezone_auto" not in profile_columns:
        op.add_column(
            "profiles",
            sa.Column(
                "timezone_auto", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
        )
    if "dia" not in profile_columns:
        op.add_column(
            "profiles",
            sa.Column("dia", sa.Float(), nullable=False, server_default="4.0"),
        )
    if "round_step" not in profile_columns:
        op.add_column(
            "profiles",
            sa.Column(
                "round_step", sa.Float(), nullable=False, server_default="0.5"
            ),
        )
    if "carb_units" not in profile_columns:
        op.add_column(
            "profiles",
            sa.Column("carb_units", sa.String(), nullable=False, server_default="g"),
        )
    if "grams_per_xe" not in profile_columns:
        op.add_column(
            "profiles",
            sa.Column(
                "grams_per_xe",
                sa.Float(),
                nullable=False,
                server_default="12.0",
            ),
        )
    if "therapy_type" not in profile_columns:
        op.add_column(
            "profiles",
            sa.Column(
                "therapy_type", sa.String(), nullable=False, server_default="insulin"
            ),
        )
    if "glucose_units" not in profile_columns:
        op.add_column(
            "profiles",
            sa.Column(
                "glucose_units",
                sa.String(),
                nullable=False,
                server_default="mmol/L",
            ),
        )
    if "insulin_type" not in profile_columns:
        op.add_column(
            "profiles", sa.Column("insulin_type", sa.String(), nullable=True)
        )
    if "prebolus_min" not in profile_columns:
        op.add_column(
            "profiles",
            sa.Column(
                "prebolus_min", sa.Integer(), nullable=False, server_default="0"
            ),
        )
    if "max_bolus" not in profile_columns:
        op.add_column(
            "profiles",
            sa.Column("max_bolus", sa.Float(), nullable=False, server_default="10.0"),
        )
    if "postmeal_check_min" not in profile_columns:
        op.add_column(
            "profiles",
            sa.Column(
                "postmeal_check_min",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )

    if "timezone_auto" in user_columns:
        if bind.dialect.name == "sqlite":
            op.execute(
                """
                UPDATE profiles
                SET timezone_auto = (
                    SELECT u.timezone_auto
                    FROM users AS u
                    WHERE profiles.telegram_id = u.telegram_id
                )
                """,
            )
        else:
            op.execute(
                """
                UPDATE profiles
                SET timezone_auto = u.timezone_auto
                FROM users AS u
                WHERE profiles.telegram_id = u.telegram_id
                """,
            )
        if bind.dialect.name == "postgresql":
            op.drop_column("users", "timezone_auto")
        else:
            with op.batch_alter_table("users") as batch_op:
                batch_op.drop_column("timezone_auto")

    with op.batch_alter_table("profiles") as batch_op:
        batch_op.alter_column(
            "timezone", existing_type=sa.String(), server_default=None
        )
        batch_op.alter_column(
            "timezone_auto", existing_type=sa.Boolean(), server_default=None
        )
        batch_op.alter_column("dia", existing_type=sa.Float(), server_default=None)
        batch_op.alter_column(
            "round_step", existing_type=sa.Float(), server_default=None
        )
        batch_op.alter_column(
            "carb_units", existing_type=sa.String(), server_default=None
        )
        batch_op.alter_column(
            "grams_per_xe", existing_type=sa.Float(), server_default=None
        )
        batch_op.alter_column(
            "therapy_type", existing_type=sa.String(), server_default=None
        )
        batch_op.alter_column(
            "glucose_units", existing_type=sa.String(), server_default=None
        )
        batch_op.alter_column(
            "prebolus_min", existing_type=sa.Integer(), server_default=None
        )
        batch_op.alter_column(
            "max_bolus", existing_type=sa.Float(), server_default=None
        )
        batch_op.alter_column(
            "postmeal_check_min", existing_type=sa.Integer(), server_default=None
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = {
        col["name"] for col in inspector.get_columns("users")
    }
    profile_columns = {
        col["name"] for col in inspector.get_columns("profiles")
    }

    if "timezone_auto" not in user_columns:
        op.add_column(
            "users",
            sa.Column(
                "timezone_auto", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
        )
        user_columns.add("timezone_auto")

    if "timezone_auto" in profile_columns:
        if bind.dialect.name == "sqlite":
            op.execute(
                """
                UPDATE users
                SET timezone_auto = (
                    SELECT p.timezone_auto
                    FROM profiles AS p
                    WHERE users.telegram_id = p.telegram_id
                )
                """,
            )
        else:
            op.execute(
                """
                UPDATE users
                SET timezone_auto = p.timezone_auto
                FROM profiles AS p
                WHERE users.telegram_id = p.telegram_id
                """,
            )

    if bind.dialect.name == "postgresql":
        if "postmeal_check_min" in profile_columns:
            op.drop_column("profiles", "postmeal_check_min")
        if "max_bolus" in profile_columns:
            op.drop_column("profiles", "max_bolus")
        if "prebolus_min" in profile_columns:
            op.drop_column("profiles", "prebolus_min")
        if "insulin_type" in profile_columns:
            op.drop_column("profiles", "insulin_type")
        if "glucose_units" in profile_columns:
            op.drop_column("profiles", "glucose_units")
        if "therapy_type" in profile_columns:
            op.drop_column("profiles", "therapy_type")
        if "grams_per_xe" in profile_columns:
            op.drop_column("profiles", "grams_per_xe")
        if "carb_units" in profile_columns:
            op.drop_column("profiles", "carb_units")
        if "round_step" in profile_columns:
            op.drop_column("profiles", "round_step")
        if "dia" in profile_columns:
            op.drop_column("profiles", "dia")
        if "timezone_auto" in profile_columns:
            op.drop_column("profiles", "timezone_auto")
        if "timezone" in profile_columns:
            op.drop_column("profiles", "timezone")
    else:
        with op.batch_alter_table("profiles") as batch_op:
            if "postmeal_check_min" in profile_columns:
                batch_op.drop_column("postmeal_check_min")
            if "max_bolus" in profile_columns:
                batch_op.drop_column("max_bolus")
            if "prebolus_min" in profile_columns:
                batch_op.drop_column("prebolus_min")
            if "insulin_type" in profile_columns:
                batch_op.drop_column("insulin_type")
            if "glucose_units" in profile_columns:
                batch_op.drop_column("glucose_units")
            if "therapy_type" in profile_columns:
                batch_op.drop_column("therapy_type")
            if "grams_per_xe" in profile_columns:
                batch_op.drop_column("grams_per_xe")
            if "carb_units" in profile_columns:
                batch_op.drop_column("carb_units")
            if "round_step" in profile_columns:
                batch_op.drop_column("round_step")
            if "dia" in profile_columns:
                batch_op.drop_column("dia")
            if "timezone_auto" in profile_columns:
                batch_op.drop_column("timezone_auto")
            if "timezone" in profile_columns:
                batch_op.drop_column("timezone")

    if "timezone_auto" in user_columns:
        op.alter_column("users", "timezone_auto", server_default=None)
