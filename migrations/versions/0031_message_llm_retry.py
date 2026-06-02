"""messages.llm_retry_needed — флаг повторной LLM-обработки при восстановлении баланса

Revision ID: 0031_message_llm_retry
Revises: 0030_vacancy_shooting_date
Create Date: 2026-06-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0031_message_llm_retry"
down_revision: Union[str, None] = "0030_vacancy_shooting_date"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "llm_retry_needed",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("messages", "llm_retry_needed")
