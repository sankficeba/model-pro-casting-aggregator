"""users.source — метка рекламного источника из /start <payload> (first touch)

Revision ID: 0035_users_source
Revises: 0034_message_links
Create Date: 2026-11-12

Ссылка вида t.me/<bot>?start=vk_ads1 передаёт боту payload «vk_ads1».
Записываем его только при создании пользователя — повторный /start с
другой меткой источник не перезаписывает. NULL = пришёл без метки.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0035_users_source"
down_revision: Union[str, None] = "0034_message_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("source", sa.String(length=64), nullable=True))
    op.create_index("ix_users_first_seen", "users", ["first_seen"])


def downgrade() -> None:
    op.drop_index("ix_users_first_seen", table_name="users")
    op.drop_column("users", "source")
