"""messages.links — ссылки из поста (скрытые text-url, url в тексте, URL-кнопки)

Revision ID: 0034_message_links
Revises: 0033_users_language
Create Date: 2026-11-12

Раньше хранили только plain text: ссылки под словами («Оригинал →
перейти») и inline-кнопки терялись, из-за чего нельзя было, например,
отследить первоисточник постов агрегаторов без чтения истории через userbot.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0034_message_links"
down_revision: Union[str, None] = "0033_users_language"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "links",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("messages", "links")
