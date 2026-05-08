"""paid subscriptions: trial + active_until + reminders + payments

Revision ID: 0022_subscriptions
Revises: 0021_broadcast_payload
Create Date: 2026-05-08

Бесплатная пробная неделя; затем периодические платежи через YooKassa.
Уведомления-напоминалки за 2 суток / сутки / 3 часа до истечения.
После истечения — degraded mode «1 сообщение в 24 часа».
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0022_subscriptions"
down_revision: Union[str, None] = "0021_broadcast_payload"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Subscription state on users
    op.add_column(
        "users",
        sa.Column(
            "subscription_active_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column("trial_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_expiry_reminder_stage", sa.String(8), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "last_notify_after_expiry_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Payments
    op.create_table(
        "payments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("yk_payment_id", sa.String(64), nullable=True, unique=True),
        sa.Column("idempotency_key", sa.String(64), nullable=False, unique=True),
        sa.Column("amount_rub", sa.Numeric(10, 2), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('pending','succeeded','canceled')",
            name="ck_payments_status",
        ),
    )
    op.create_index(
        "ix_payments_user_created",
        "payments",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_payments_user_created", table_name="payments")
    op.drop_table("payments")
    op.drop_column("users", "last_notify_after_expiry_at")
    op.drop_column("users", "last_expiry_reminder_stage")
    op.drop_column("users", "trial_started_at")
    op.drop_column("users", "subscription_active_until")
