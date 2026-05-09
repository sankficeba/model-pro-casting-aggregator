"""favorites + channels.invite_link

Revision ID: 0023_favorites
Revises: 0022_subscriptions
Create Date: 2026-05-09

Кнопки «Подробнее / Удалить / Добавить в избранное» под кастинг-уведомлениями:
- channels.invite_link — ручная ссылка для приватных каналов.
- favorites — сохранённые юзером сообщения, рендерятся в Mini App.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0023_favorites"
down_revision: Union[str, None] = "0022_subscriptions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "channels",
        sa.Column("invite_link", sa.String(256), nullable=True),
    )

    op.create_table(
        "favorites",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "message_id",
            sa.Integer(),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "matched_vacancy_ids",
            postgresql.ARRAY(sa.Integer()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "message_id", name="uq_favorites_user_message"),
    )
    op.create_index("ix_favorites_user_created", "favorites", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_favorites_user_created", table_name="favorites")
    op.drop_table("favorites")
    op.drop_column("channels", "invite_link")
