"""users.bot_chat_active — отметка о наличии активного чата с ботом

Revision ID: 0028_users_bot_chat_active
Revises: 0027_backfill_joined_at
Create Date: 2026-05-12

При попытке send_message/copy_message Telegram отвечает
«Bad Request: chat not found» / «Forbidden: bot was blocked by the
user» если у юзера нет активного диалога с ботом (никогда не нажимал
/start, удалил аккаунт, заблокировал бота). После первой такой ошибки
помечаем юзера inactive и исключаем из будущих рассылок.

Default TRUE — все существующие юзеры считаются активными до доказательства
обратного.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0028_users_bot_chat_active"
down_revision: Union[str, None] = "0027_backfill_joined_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "bot_chat_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "bot_chat_active")
