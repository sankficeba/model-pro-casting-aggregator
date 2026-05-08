"""user delivery modes + pending_notifications queue + night mode

Revision ID: 0018_delivery_modes
Revises: 0017_user_blacklist
Create Date: 2026-05-08

Юзер выбирает как получать уведомления:
- 'instant' — сразу как только появляется кастинг (default).
- 'digest' — копятся, юзер просматривает их вручную через бот-кнопки.
Дополнительно night mode: в указанный диапазон часов (по MSK) уведомления
попадают в очередь, утром приходит digest «за ночь — N кастингов».
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0018_delivery_modes"
down_revision: Union[str, None] = "0017_user_blacklist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users settings ---
    op.add_column(
        "users",
        sa.Column("delivery_mode", sa.String(16), nullable=False, server_default="instant"),
    )
    op.create_check_constraint(
        "ck_users_delivery_mode",
        "users",
        "delivery_mode IN ('instant','digest')",
    )
    op.add_column(
        "users",
        sa.Column("night_mode_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("night_start_hour", sa.Integer(), nullable=False, server_default="23"),
    )
    op.add_column(
        "users",
        sa.Column("night_end_hour", sa.Integer(), nullable=False, server_default="9"),
    )
    op.add_column(
        "users",
        sa.Column(
            "night_digest_last_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_users_night_hours",
        "users",
        "night_start_hour BETWEEN 0 AND 23 AND night_end_hour BETWEEN 0 AND 23",
    )

    # --- pending_notifications queue ---
    op.create_table(
        "pending_notifications",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "message_id",
            sa.Integer(),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text_hash", sa.String(40), nullable=True),
        sa.Column("matched_vacancy_ids", sa.dialects.postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Тот же дедуп: (user_id, message_id) и (user_id, text_hash) — нельзя
        # положить в очередь повторно по тому же тексту.
        sa.UniqueConstraint("user_id", "message_id", name="uq_pending_user_msg"),
    )
    op.create_index(
        "ix_pending_user",
        "pending_notifications",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_pending_user_texthash",
        "pending_notifications",
        ["user_id", "text_hash"],
        unique=True,
        postgresql_where=sa.text("text_hash IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_pending_user_texthash", table_name="pending_notifications")
    op.drop_index("ix_pending_user", table_name="pending_notifications")
    op.drop_table("pending_notifications")
    op.drop_constraint("ck_users_night_hours", "users", type_="check")
    op.drop_column("users", "night_digest_last_sent_at")
    op.drop_column("users", "night_end_hour")
    op.drop_column("users", "night_start_hour")
    op.drop_column("users", "night_mode_enabled")
    op.drop_constraint("ck_users_delivery_mode", "users", type_="check")
    op.drop_column("users", "delivery_mode")
