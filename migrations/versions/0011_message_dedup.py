"""messages: text_hash + canonical_message_id for forward-dedup

Revision ID: 0011_message_dedup
Revises: 0010_channels_tg_chat_id
Create Date: 2026-05-07

Один и тот же кастинг расходится по 30+ каналам через форвард или
copy-paste. Чтобы не спамить пользователя одним и тем же объявлением:

- text_hash: SHA-1 от нормализованного текста (см. db/dedup.py).
- canonical_message_id: self-FK на первый row с этим хэшем. У canonical
  (= оригинальной публикации) — NULL.

Бэкфилл не делаем: исторические row'ы старше 7-дневного окна, в
лукап не попадают. Новые сообщения получат hash сразу.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0011_message_dedup"
down_revision: Union[str, None] = "0010_channels_tg_chat_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("text_hash", sa.CHAR(40), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("canonical_message_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_messages_canonical",
        source_table="messages",
        referent_table="messages",
        local_cols=["canonical_message_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )
    # Partial index по горячему пути — лукап canonical-row'ов в окне.
    op.execute(
        "CREATE INDEX ix_messages_text_hash_recent "
        "ON messages (text_hash, received_at DESC) "
        "WHERE canonical_message_id IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_messages_text_hash_recent")
    op.drop_constraint("fk_messages_canonical", "messages", type_="foreignkey")
    op.drop_column("messages", "canonical_message_id")
    op.drop_column("messages", "text_hash")
