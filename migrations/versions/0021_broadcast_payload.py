"""admin broadcast: store demographic filters payload

Revision ID: 0021_broadcast_payload
Revises: 0020_admin_broadcast
Create Date: 2026-05-08

Расширяем pending-state админа: помимо scope-кода (все/per-category)
сохраняем выбранные демографические фильтры (возраст/рост/ФИО).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "0021_broadcast_payload"
down_revision: Union[str, None] = "0020_admin_broadcast"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("broadcast_pending_payload", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "broadcast_pending_payload")
