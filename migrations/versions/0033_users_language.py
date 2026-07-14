"""users.language — ручной оверрайд языка интерфейса бота (ru/en)

Revision ID: 0033_users_language
Revises: 0032_creative_experience_text
Create Date: 2026-07-14

По умолчанию язык определяется на лету из Telegram
`from_user.language_code` (en → английский, всё остальное → русский).
Колонка хранит явный выбор через /language, если юзер его сделал —
он должен пережить смену языка клиента Telegram. NULL = не выбирал,
используем auto-detect.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0033_users_language"
down_revision: Union[str, None] = "0032_creative_experience_text"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("language", sa.String(length=8), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "language")
