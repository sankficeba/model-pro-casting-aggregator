"""admin broadcast: pending state on users

Revision ID: 0020_admin_broadcast
Revises: 0019_daily_digest
Create Date: 2026-05-08

Когда админ нажимает «Отправить рассылку» в Mini App, мы сохраняем у его
user-row код фильтра аудитории и timestamp. Бот при следующем сообщении
этого админа (текст/фото/видео/гиф) копирует его всем подходящим юзерам
через copyMessage и очищает поля.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0020_admin_broadcast"
down_revision: Union[str, None] = "0019_daily_digest"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("broadcast_pending_filter", sa.String(16), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "broadcast_pending_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "broadcast_pending_at")
    op.drop_column("users", "broadcast_pending_filter")
