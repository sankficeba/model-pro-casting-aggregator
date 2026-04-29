"""vacancies: add ethnicity + height_min/height_max

Revision ID: 0008_vacancy_eth_height
Revises: 0007_vacancies
Create Date: 2026-04-30

В вакансиях встречаются дополнительные требования: этническая внешность
(славянская, азиатская и т.п.) и рост. Раньше эти параметры не извлекались
и не учитывались при матчинге, поэтому пользователи получали уведомления
о неподходящих ролях.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0008_vacancy_eth_height"
down_revision: Union[str, None] = "0007_vacancies"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "vacancies",
        sa.Column(
            "ethnicity", sa.ARRAY(sa.Text()),
            nullable=False, server_default=sa.text("'{}'::text[]"),
        ),
    )
    op.add_column("vacancies", sa.Column("height_min", sa.Integer(), nullable=True))
    op.add_column("vacancies", sa.Column("height_max", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("vacancies", "height_max")
    op.drop_column("vacancies", "height_min")
    op.drop_column("vacancies", "ethnicity")
