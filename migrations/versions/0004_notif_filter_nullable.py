"""notifications.filter_id nullable + drop FK

Revision ID: 0004_notifications_filter_id_nullable
Revises: 0003_actor_profile_completed_at
Create Date: 2026-04-29

Старая модель уведомлений была привязана к filters.id (фильтру, который
триггернул рассылку). Сейчас матчинг идёт по actor_profiles, поэтому
filter_id больше не имеет смысла — делаем его nullable и убираем FK.
Существующие строки сохраняются.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_notifications_filter_id_nullable"
down_revision: Union[str, None] = "0003_actor_profile_completed_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Дропаем FK, имя дефолтное — notifications_filter_id_fkey.
    op.drop_constraint(
        "notifications_filter_id_fkey",
        "notifications",
        type_="foreignkey",
    )
    op.alter_column(
        "notifications",
        "filter_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "notifications",
        "filter_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_foreign_key(
        "notifications_filter_id_fkey",
        "notifications",
        "filters",
        ["filter_id"],
        ["id"],
        ondelete="CASCADE",
    )
