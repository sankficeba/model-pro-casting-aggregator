"""dedup race fix: backfill canonical + notifications text_hash + UNIQUE

Revision ID: 0015_dedup_race_fix
Revises: 0014_experience_text
Create Date: 2026-05-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0015_dedup_race_fix"
down_revision: Union[str, None] = "0014_experience_text"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Backfill: связать существующих двойников в messages с самым ранним
    #    canonical-row'ом с тем же text_hash.
    op.execute(
        """
        UPDATE messages
        SET canonical_message_id = m.canonical_id
        FROM (
          SELECT text_hash, MIN(id) AS canonical_id
          FROM messages
          WHERE canonical_message_id IS NULL AND text_hash IS NOT NULL
          GROUP BY text_hash
        ) m
        WHERE messages.text_hash = m.text_hash
          AND messages.canonical_message_id IS NULL
          AND messages.id != m.canonical_id;
        """
    )

    # 2. Денормализация: text_hash в notifications
    op.add_column(
        "notifications",
        sa.Column("text_hash", sa.String(40), nullable=True),
    )

    # 3. Backfill text_hash из messages
    op.execute(
        """
        UPDATE notifications n
        SET text_hash = m.text_hash
        FROM messages m
        WHERE n.message_id = m.id AND m.text_hash IS NOT NULL;
        """
    )

    # 4. Удалить существующие дубли нотификаций (оставляем самую раннюю
    #    по id; UNIQUE-индекс ниже не накатился бы при их наличии).
    op.execute(
        """
        DELETE FROM notifications n
        USING notifications dup
        WHERE n.user_id = dup.user_id
          AND n.text_hash = dup.text_hash
          AND n.text_hash IS NOT NULL
          AND n.id > dup.id;
        """
    )

    # 5. Partial UNIQUE-индекс: один user × один text_hash = одно уведомление.
    #    Исторические записи с text_hash IS NULL не участвуют.
    op.create_index(
        "ix_notifications_user_texthash",
        "notifications",
        ["user_id", "text_hash"],
        unique=True,
        postgresql_where=sa.text("text_hash IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_texthash", table_name="notifications")
    op.drop_column("notifications", "text_hash")
    # Backfill canonical_message_id не откатываем — это data fix, не схема.
