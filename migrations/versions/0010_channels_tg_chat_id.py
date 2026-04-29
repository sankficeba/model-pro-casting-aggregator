"""channels: nullable username + tg_chat_id for private channels

Revision ID: 0010_channels_tg_chat_id
Revises: 0009_vacancy_body_hair
Create Date: 2026-04-30

Раньше канал хранился только по `@username`. Приватные группы и каналы,
доступные через `https://t.me/c/<id>`, не могут быть добавлены, потому
что у них нет публичного username. Добавляем колонку `tg_chat_id` с
полным каналным id (формы -100<chat_id>) и делаем `username` опциональной.
Хотя бы одно из двух должно быть задано — на уровне DB CHECK constraint.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0010_channels_tg_chat_id"
down_revision: Union[str, None] = "0009_vacancy_body_hair"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("channels", "username", nullable=True)
    op.add_column(
        "channels",
        sa.Column("tg_chat_id", sa.BigInteger(), nullable=True),
    )
    op.create_unique_constraint("uq_channels_tg_chat_id", "channels", ["tg_chat_id"])
    op.create_check_constraint(
        "ck_channels_username_or_chat_id",
        "channels",
        "username IS NOT NULL OR tg_chat_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_channels_username_or_chat_id", "channels", type_="check")
    op.drop_constraint("uq_channels_tg_chat_id", "channels", type_="unique")
    op.drop_column("channels", "tg_chat_id")
    op.alter_column("channels", "username", nullable=False)
