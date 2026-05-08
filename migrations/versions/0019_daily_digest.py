"""digest mode: daily-time push toggle + manual review trigger

Revision ID: 0019_daily_digest
Revises: 0018_delivery_modes
Create Date: 2026-05-08

В digest-режиме раньше уведомления приходили только если юзер сам набирал
/review или нажимал кнопку «Далее». Добавляем опциональную ежедневную
push-плашку «За сегодня — N кастингов, посмотреть?» в указанный час МСК.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0019_daily_digest"
down_revision: Union[str, None] = "0018_delivery_modes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "digest_daily_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "digest_daily_hour",
            sa.Integer(),
            nullable=False,
            server_default="20",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "digest_daily_last_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_users_digest_daily_hour",
        "users",
        "digest_daily_hour BETWEEN 0 AND 23",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_digest_daily_hour", "users", type_="check")
    op.drop_column("users", "digest_daily_last_sent_at")
    op.drop_column("users", "digest_daily_hour")
    op.drop_column("users", "digest_daily_enabled")
