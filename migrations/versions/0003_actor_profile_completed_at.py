"""actor_profiles.completed_at

Revision ID: 0003_actor_profile_completed_at
Revises: 0002_actor_profiles
Create Date: 2026-04-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_actor_profile_completed_at"
down_revision: Union[str, None] = "0002_actor_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "actor_profiles",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("actor_profiles", "completed_at")
