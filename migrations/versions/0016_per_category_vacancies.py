"""per-category matching: messages.category + vacancies.category + work_types

Revision ID: 0016_per_category_vacancies
Revises: 0015_dedup_race_fix
Create Date: 2026-05-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY


revision: str = "0016_per_category_vacancies"
down_revision: Union[str, None] = "0015_dedup_race_fix"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Старая колонка messages.category (legacy, String(64)) переименовывается,
    # чтобы не конфликтовать с новой category (per-category matching, String(16)).
    # Старые данные в этой колонке кодом не используются.
    op.alter_column("messages", "category", new_column_name="legacy_category")

    # Новая колонка messages.category (per-category matching).
    op.add_column(
        "messages",
        sa.Column("category", sa.String(16), nullable=True),
    )
    op.create_check_constraint(
        "ck_messages_category",
        "messages",
        "category IS NULL OR category IN ('creative','event','general','admin')",
    )
    op.create_index(
        "ix_messages_category",
        "messages",
        ["category"],
        postgresql_where=sa.text("category IS NOT NULL"),
    )

    # vacancies.category + vacancies.work_types
    op.add_column(
        "vacancies",
        sa.Column("category", sa.String(16), nullable=True),
    )
    op.add_column(
        "vacancies",
        sa.Column("work_types", ARRAY(sa.Text()), nullable=False, server_default="{}"),
    )
    op.create_check_constraint(
        "ck_vacancies_category",
        "vacancies",
        "category IS NULL OR category IN ('creative','event','general','admin')",
    )

    # Бэкфилл: исторические casting-посты — все creative (LLM до этой
    # миграции извлекал только creative-схему).
    op.execute("UPDATE messages SET category = 'creative' WHERE is_casting = TRUE")


def downgrade() -> None:
    op.drop_constraint("ck_vacancies_category", "vacancies", type_="check")
    op.drop_column("vacancies", "work_types")
    op.drop_column("vacancies", "category")
    op.drop_index("ix_messages_category", table_name="messages")
    op.drop_constraint("ck_messages_category", "messages", type_="check")
    op.drop_column("messages", "category")
    op.alter_column("messages", "legacy_category", new_column_name="category")
