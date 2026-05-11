"""channels.joined_at — отметка о фактическом вступлении

Revision ID: 0026_channels_joined_at
Revises: 0025_channels_invite_check
Create Date: 2026-05-11

До сих пор userbot при каждом старте вызывал JoinChannelRequest для
каждого public-канала — даже когда мы уже были участниками. Telegram
быстро упирается в свой бюджет (~30 join/мин) и шлёт FloodWait. Мы
логировали warning и всё равно добавляли entity в filter — но
по факту НЕ были участниками, значит NewMessage events не приходили.

`joined_at`: NULL до первого успешного вступления (или подтверждения
через UserAlreadyParticipantError). После этого `_resolve_one` пропускает
JoinChannel-вызов. Retry-цикл периодически пытается вступить в каналы
с NULL.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0026_channels_joined_at"
down_revision: Union[str, None] = "0025_channels_invite_check"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "channels",
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_channels_pending_join",
        "channels",
        ["id"],
        postgresql_where=sa.text("active AND joined_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_channels_pending_join", table_name="channels")
    op.drop_column("channels", "joined_at")
