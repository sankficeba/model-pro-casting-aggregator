"""vacancies: add body_type, hair_color, hair_length

Revision ID: 0009_vacancy_body_hair
Revises: 0008_vacancy_eth_height
Create Date: 2026-04-30

В вакансиях встречаются требования по телосложению (худощавый/спортивный),
цвету и длине волос. Раньше эти поля не извлекались, и пользователи
получали уведомления о неподходящих ролях.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0009_vacancy_body_hair"
down_revision: Union[str, None] = "0008_vacancy_eth_height"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_array_text(name: str) -> None:
    op.add_column(
        "vacancies",
        sa.Column(
            name, sa.ARRAY(sa.Text()),
            nullable=False, server_default=sa.text("'{}'::text[]"),
        ),
    )


def upgrade() -> None:
    _add_array_text("body_type")
    _add_array_text("hair_color")
    _add_array_text("hair_length")


def downgrade() -> None:
    op.drop_column("vacancies", "hair_length")
    op.drop_column("vacancies", "hair_color")
    op.drop_column("vacancies", "body_type")
