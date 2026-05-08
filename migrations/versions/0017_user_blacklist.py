"""user blacklisted_words for filtering notifications

Revision ID: 0017_user_blacklist
Revises: 0016_per_category_vacancies
Create Date: 2026-05-08

Юзер указывает слова/фразы, при наличии которых в тексте поста ему
не приходит уведомление. Хранится как ARRAY(Text) на User. Сравнение
case-insensitive (нижним регистром).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY


revision: str = "0017_user_blacklist"
down_revision: Union[str, None] = "0016_per_category_vacancies"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "blacklisted_words",
            ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "blacklisted_words")
