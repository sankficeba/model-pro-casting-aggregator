"""vacancies.shooting_date — дата кастинга/съёмки

Revision ID: 0030_vacancy_shooting_date
Revises: 0029_favorites_retention
Create Date: 2026-05-13

Свободный текст («3 мая», «27.05», «13-14.06») — то, что LLM
извлекает из поста. Отображается отдельной строкой в нотификации
с premium-calendar-эмодзи.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0030_vacancy_shooting_date"
down_revision: Union[str, None] = "0029_favorites_retention"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "vacancies",
        sa.Column("shooting_date", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vacancies", "shooting_date")
