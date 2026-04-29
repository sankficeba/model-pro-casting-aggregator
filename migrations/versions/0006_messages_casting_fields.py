"""messages: add casting-specific columns

Revision ID: 0006_messages_casting
Revises: 0005_channels
Create Date: 2026-04-29

Раньше LLM-extract сжимался в три старые колонки (gender, age, category).
Теперь сохраняем оригинальную структуру: is_casting, диапазон возраста,
коды проектов/ролей, город и ставку. Старые колонки оставляем для
исторических строк и обратной совместимости — в новых записях они
больше не заполняются.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_messages_casting"
down_revision: Union[str, None] = "0005_channels"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "is_casting",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column("messages", sa.Column("age_min", sa.Integer(), nullable=True))
    op.add_column("messages", sa.Column("age_max", sa.Integer(), nullable=True))
    op.add_column(
        "messages",
        sa.Column(
            "project_types",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
    )
    op.add_column(
        "messages",
        sa.Column(
            "role_types",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
    )
    op.add_column(
        "messages",
        sa.Column("city", sa.String(length=64), nullable=True),
    )
    op.add_column("messages", sa.Column("rate", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "rate")
    op.drop_column("messages", "city")
    op.drop_column("messages", "role_types")
    op.drop_column("messages", "project_types")
    op.drop_column("messages", "age_max")
    op.drop_column("messages", "age_min")
    op.drop_column("messages", "is_casting")
