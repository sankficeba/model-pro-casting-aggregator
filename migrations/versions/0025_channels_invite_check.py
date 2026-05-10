"""channels: relax CHECK to also accept invite_link

Revision ID: 0025_channels_invite_check
Revises: 0024_problems
Create Date: 2026-05-10

Приватные каналы по invite-ссылке (`https://t.me/+xxx`) хранятся с
username=NULL, tg_chat_id=NULL до первого `ImportChatInviteRequest`,
после которого userbot записывает entity.id в tg_chat_id. На момент
INSERT/UPDATE такой строки старый CHECK
(username IS NOT NULL OR tg_chat_id IS NOT NULL) фейлился.

Расширяем условие: достаточно одного из трёх полей.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0025_channels_invite_check"
down_revision: Union[str, None] = "0024_problems"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_channels_username_or_chat_id", "channels", type_="check"
    )
    op.create_check_constraint(
        "ck_channels_username_or_chat_id",
        "channels",
        "username IS NOT NULL OR tg_chat_id IS NOT NULL OR invite_link IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_channels_username_or_chat_id", "channels", type_="check"
    )
    op.create_check_constraint(
        "ck_channels_username_or_chat_id",
        "channels",
        "username IS NOT NULL OR tg_chat_id IS NOT NULL",
    )
