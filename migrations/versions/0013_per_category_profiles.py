"""per-category profile tables

Revision ID: 0013_per_category_profiles
Revises: 0012_user_category_subscription
Create Date: 2026-05-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY


revision: str = "0013_per_category_profiles"
down_revision: Union[str, None] = "0012_user_category_subscription"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _common_columns():
    return [
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("full_name", sa.String(128), nullable=True),
        sa.Column("gender", sa.String(8), nullable=True),
        sa.Column("city", sa.String(64), nullable=True),
        sa.Column("ready_for_travel", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("actual_age", sa.Integer(), nullable=True),
        sa.Column("min_rate", sa.Integer(), nullable=True),
        sa.Column("tax_status", sa.String(32), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("vk_url", sa.Text(), nullable=True),
        sa.Column("telegram_user", sa.String(64), nullable=True),
        sa.Column("email", sa.String(128), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    ]


def upgrade() -> None:
    # creative_profile — все поля старой actor_profile + telegram_user
    op.create_table(
        "creative_profile",
        *_common_columns(),
        sa.Column("play_age_min", sa.Integer(), nullable=True),
        sa.Column("play_age_max", sa.Integer(), nullable=True),
        sa.Column("project_types", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("role_types", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("show_negotiable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("show_noncommercial", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_agency", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("clothing_size", sa.Integer(), nullable=True),
        sa.Column("shoe_size", sa.Integer(), nullable=True),
        sa.Column("ethnicity", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("body_type", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("hair_color", sa.String(32), nullable=True),
        sa.Column("hair_length", sa.String(32), nullable=True),
        sa.Column("has_experience", sa.Boolean(), nullable=True),
        sa.Column("education", sa.String(32), nullable=True),
        sa.Column("eye_color", sa.String(32), nullable=True),
        sa.Column("marks", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("skills_sport", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("skills_dance", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("skills_vocal", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("skills_instruments", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("portfolio_url", sa.Text(), nullable=True),
        sa.Column("video_url", sa.Text(), nullable=True),
        sa.Column("professional_url", sa.Text(), nullable=True),
    )
    # event_profile
    op.create_table(
        "event_profile",
        *_common_columns(),
        sa.Column("show_negotiable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("show_noncommercial", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("clothing_size", sa.Integer(), nullable=True),
        sa.Column("shoe_size", sa.Integer(), nullable=True),
        sa.Column("ethnicity", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("body_type", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("hair_color", sa.String(32), nullable=True),
        sa.Column("hair_length", sa.String(32), nullable=True),
        sa.Column("work_types", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("has_experience", sa.Boolean(), nullable=True),
        sa.Column("portfolio_url", sa.Text(), nullable=True),
        sa.Column("video_url", sa.Text(), nullable=True),
    )
    # general_profile
    op.create_table(
        "general_profile",
        *_common_columns(),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("physical_fitness", sa.String(16), nullable=True),
        sa.Column("work_types", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("has_experience", sa.Boolean(), nullable=True),
        sa.CheckConstraint(
            "physical_fitness IS NULL OR physical_fitness IN ('light','medium','heavy')",
            name="ck_general_profile_physical_fitness",
        ),
    )
    # admin_profile
    op.create_table(
        "admin_profile",
        *_common_columns(),
        sa.Column("education", sa.String(32), nullable=True),
        sa.Column("work_types", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("has_experience", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("admin_profile")
    op.drop_table("general_profile")
    op.drop_table("event_profile")
    op.drop_table("creative_profile")
