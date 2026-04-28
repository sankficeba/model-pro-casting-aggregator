"""actor_profiles table

Revision ID: 0002_actor_profiles
Revises: 0001_initial
Create Date: 2026-04-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_actor_profiles"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "actor_profiles",
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        # Step 1
        sa.Column("full_name", sa.String(length=128), nullable=True),
        sa.Column("gender", sa.String(length=8), nullable=True),
        sa.Column("city", sa.String(length=64), nullable=True),
        sa.Column("ready_for_travel", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("actual_age", sa.Integer(), nullable=True),
        sa.Column("play_age_min", sa.Integer(), nullable=True),
        sa.Column("play_age_max", sa.Integer(), nullable=True),
        # Step 2
        sa.Column(
            "project_types",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "role_types",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("min_rate", sa.Integer(), nullable=True),
        sa.Column("show_negotiable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("show_noncommercial", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("show_agency", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        # Step 3
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("clothing_size", sa.Integer(), nullable=True),
        sa.Column("shoe_size", sa.Integer(), nullable=True),
        sa.Column(
            "ethnicity",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "body_type",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("hair_color", sa.String(length=32), nullable=True),
        sa.Column("hair_length", sa.String(length=32), nullable=True),
        # Step 4
        sa.Column("has_experience", sa.Boolean(), nullable=True),
        sa.Column("education", sa.String(length=32), nullable=True),
        sa.Column("tax_status", sa.String(length=32), nullable=True),
        # Step 5
        sa.Column("eye_color", sa.String(length=32), nullable=True),
        sa.Column(
            "marks",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "skills_sport",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "skills_dance",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "skills_vocal",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "skills_instruments",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        # Step 6
        sa.Column("portfolio_url", sa.Text(), nullable=True),
        sa.Column("video_url", sa.Text(), nullable=True),
        sa.Column("professional_url", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("vk_url", sa.Text(), nullable=True),
        sa.Column("email", sa.String(length=128), nullable=True),
        # timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("actor_profiles")
