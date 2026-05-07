"""experience_text on event_profile, general_profile and admin_profile

Revision ID: 0014_experience_text
Revises: 0013_per_category_profiles
Create Date: 2026-05-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0014_experience_text"
down_revision: Union[str, None] = "0013_per_category_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "event_profile",
        sa.Column("experience_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "general_profile",
        sa.Column("experience_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "admin_profile",
        sa.Column("experience_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("admin_profile", "experience_text")
    op.drop_column("general_profile", "experience_text")
    op.drop_column("event_profile", "experience_text")
