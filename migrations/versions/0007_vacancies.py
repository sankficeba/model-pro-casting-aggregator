"""vacancies table + matched_vacancy_ids on notifications

Revision ID: 0007_vacancies
Revises: 0006_messages_casting
Create Date: 2026-04-29

Разводим «пост» и «вакансию»: один Telegram-пост может описывать
несколько ролей с разными условиями. Старые post-level колонки в
`messages` (gender, age_min, age_max, role_types, rate) физически
оставляем для исторических данных и для безопасного rollback —
новый код их не пишет.

Бэкфилл: на каждый исторический is_casting=true пост создаётся одна
вакансия (idx=0) с полями, скопированными из messages.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0007_vacancies"
down_revision: Union[str, None] = "0006_messages_casting"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vacancies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "message_id", sa.Integer(),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column(
            "role_types", sa.ARRAY(sa.Text()),
            nullable=False, server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("gender", sa.String(length=8), nullable=True),
        sa.Column("age_min", sa.Integer(), nullable=True),
        sa.Column("age_max", sa.Integer(), nullable=True),
        sa.Column("rate", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("role_label", sa.String(length=128), nullable=True),
        sa.UniqueConstraint("message_id", "idx", name="uq_vacancies_message_idx"),
    )
    op.create_index(
        "ix_vacancies_message_id", "vacancies", ["message_id"], unique=False,
    )

    op.add_column(
        "notifications",
        sa.Column("matched_vacancy_ids", sa.ARRAY(sa.Integer()), nullable=True),
    )

    # Бэкфилл: 1 вакансия на каждое историческое is_casting=true сообщение.
    op.execute(
        """
        INSERT INTO vacancies (
            message_id, idx, role_types, gender, age_min, age_max,
            rate, description, role_label
        )
        SELECT
            m.id,
            0,
            COALESCE(m.role_types, '{}'::text[]),
            m.gender,
            m.age_min,
            m.age_max,
            m.rate,
            m.summary,
            NULL
        FROM messages m
        WHERE m.is_casting = true
        """
    )


def downgrade() -> None:
    op.drop_column("notifications", "matched_vacancy_ids")
    op.drop_index("ix_vacancies_message_id", table_name="vacancies")
    op.drop_table("vacancies")
