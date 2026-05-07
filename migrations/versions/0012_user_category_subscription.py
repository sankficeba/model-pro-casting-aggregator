"""user_category_subscription

Revision ID: 0012_user_category_subscription
Revises: 0011_message_dedup
Create Date: 2026-05-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0012_user_category_subscription"
down_revision: Union[str, None] = "0011_message_dedup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_category_subscription",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        ),
        sa.CheckConstraint(
            "category IN ('creative','event','general','admin')",
            name="ck_user_category_subscription_category",
        ),
        sa.UniqueConstraint("user_id", "category", name="uq_user_category"),
    )
    op.create_index(
        "ix_user_category_subscription_user_id",
        "user_category_subscription",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_category_subscription_user_id", table_name="user_category_subscription")
    op.drop_table("user_category_subscription")
