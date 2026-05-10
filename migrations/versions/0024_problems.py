"""problems table

Revision ID: 0024_problems
Revises: 0023_favorites
Create Date: 2026-05-10

Кнопка «Сообщить о проблеме» в Mini App: пользователь оставляет
описание, админ получает push с кнопкой «Проблема решена».
Активные проблемы видны в админ-панели.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0024_problems"
down_revision: Union[str, None] = "0023_favorites"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "problems",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "resolved",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_problems_active_created",
        "problems",
        ["created_at"],
        postgresql_where=sa.text("resolved = false"),
    )


def downgrade() -> None:
    op.drop_index("ix_problems_active_created", table_name="problems")
    op.drop_table("problems")
