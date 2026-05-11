"""Backfill channels.joined_at для каналов-говорунов

Revision ID: 0027_backfill_joined_at
Revises: 0026_channels_joined_at
Create Date: 2026-05-11

Если канал хоть раз присылал нам сообщение — userbot фактически
в нём состоит. Чтобы 0026 не отправил эти 91 канал в pending-pool
(и не вызвал burst JoinChannelRequest при следующем рестарте),
проставляем joined_at = added_at для них.

Silent-каналы (joined_at IS NULL) подхватит retry-цикл.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0027_backfill_joined_at"
down_revision: Union[str, None] = "0026_channels_joined_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE channels c SET joined_at = c.added_at
        WHERE c.joined_at IS NULL
          AND EXISTS (
            SELECT 1 FROM messages m WHERE
                (c.username IS NOT NULL AND m.tg_chat_username ILIKE c.username)
                OR (c.tg_chat_id IS NOT NULL AND m.tg_chat_id = c.tg_chat_id)
        )
    """)


def downgrade() -> None:
    # Backfill можно сбросить, удалив joined_at, но это уровень 0026.
    pass
