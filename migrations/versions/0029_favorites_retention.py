"""users.favorites_retention_days

Revision ID: 0029_favorites_retention
Revises: 0028_users_bot_chat_active
Create Date: 2026-05-13

Срок автоудаления избранных вакансий: N дней (1-90), 0 = не удалять.
Дефолт 5 дней — кастинги быстро устаревают, держать дольше обычно нет смысла.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0029_favorites_retention"
down_revision: Union[str, None] = "0028_users_bot_chat_active"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "favorites_retention_days",
            sa.Integer(),
            nullable=False,
            server_default="5",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "favorites_retention_days")
