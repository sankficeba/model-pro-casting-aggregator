"""creative_profile и actor_profiles: добавить experience_text

Revision ID: 0032_creative_experience_text
Revises: 0031_message_llm_retry
Create Date: 2026-06-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0032_creative_experience_text"
down_revision: Union[str, None] = "0031_message_llm_retry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("creative_profile", sa.Column("experience_text", sa.Text(), nullable=True))
    op.add_column("actor_profiles", sa.Column("experience_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("creative_profile", "experience_text")
    op.drop_column("actor_profiles", "experience_text")
