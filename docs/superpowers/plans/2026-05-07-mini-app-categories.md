# Mini App Categories Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Превратить единую анкету `ActorProfile` в опросник 4 категорий + 4 независимые формы + autocomplete-подсказки + settings.

**Architecture:** Новая таблица `user_category_subscription` (multi-row флаги вкл/выкл) и 4 таблицы профилей (`creative_profile`, `event_profile`, `general_profile`, `admin_profile`), каждая со своими полями и `completed_at`. Frontend — state machine `survey → menu → form(category) → settings`. Старая `actor_profile` остаётся read-only для аудита; матчер переключается на `creative_profile`.

**Tech Stack:** SQLAlchemy 2.0 async + Alembic, FastAPI + Pydantic v2, React + TypeScript + Vite + Tailwind, aiogram v3 (только для GREETING), pytest.

**Spec:** `docs/superpowers/specs/2026-05-07-mini-app-categories-design.md`.

---

## Task 1: Миграции и SQLAlchemy-модели

**Files:**
- Create: `migrations/versions/0012_user_category_subscription.py`
- Create: `migrations/versions/0013_per_category_profiles.py`
- Modify: `db/models.py` (добавить 5 классов: `UserCategorySubscription`, `CreativeProfile`, `EventProfile`, `GeneralProfile`, `AdminProfile`)

- [ ] **Step 1: Написать миграцию 0012**

```python
# migrations/versions/0012_user_category_subscription.py
"""user_category_subscription

Revision ID: 0012_user_category_subscription
Revises: 0011_message_dedup
Create Date: 2026-05-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0012_user_category_subscription"
down_revision: Union[str, None] = "0011_message_dedup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_category_subscription",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "category IN ('creative','event','general','admin')",
            name="ck_user_category_subscription_category",
        ),
        sa.UniqueConstraint("user_id", "category", name="uq_user_category"),
    )
    op.create_index(
        "ix_user_category_subscription_user_id",
        "user_category_subscription",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_category_subscription_user_id", table_name="user_category_subscription")
    op.drop_table("user_category_subscription")
```

- [ ] **Step 2: Написать миграцию 0013** (4 таблицы профилей)

```python
# migrations/versions/0013_per_category_profiles.py
"""per-category profile tables

Revision ID: 0013_per_category_profiles
Revises: 0012_user_category_subscription
Create Date: 2026-05-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY


revision: str = "0013_per_category_profiles"
down_revision: Union[str, None] = "0012_user_category_subscription"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _common_columns():
    return [
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("full_name", sa.String(128), nullable=True),
        sa.Column("gender", sa.String(8), nullable=True),
        sa.Column("city", sa.String(64), nullable=True),
        sa.Column("ready_for_travel", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("actual_age", sa.Integer(), nullable=True),
        sa.Column("min_rate", sa.Integer(), nullable=True),
        sa.Column("tax_status", sa.String(32), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("vk_url", sa.Text(), nullable=True),
        sa.Column("telegram_user", sa.String(64), nullable=True),
        sa.Column("email", sa.String(128), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    ]


def upgrade() -> None:
    # creative_profile — все поля старой actor_profile + telegram_user
    op.create_table(
        "creative_profile",
        *_common_columns(),
        sa.Column("play_age_min", sa.Integer(), nullable=True),
        sa.Column("play_age_max", sa.Integer(), nullable=True),
        sa.Column("project_types", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("role_types", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("show_negotiable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("show_noncommercial", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_agency", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("clothing_size", sa.Integer(), nullable=True),
        sa.Column("shoe_size", sa.Integer(), nullable=True),
        sa.Column("ethnicity", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("body_type", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("hair_color", sa.String(32), nullable=True),
        sa.Column("hair_length", sa.String(32), nullable=True),
        sa.Column("has_experience", sa.Boolean(), nullable=True),
        sa.Column("education", sa.String(32), nullable=True),
        sa.Column("eye_color", sa.String(32), nullable=True),
        sa.Column("marks", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("skills_sport", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("skills_dance", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("skills_vocal", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("skills_instruments", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("portfolio_url", sa.Text(), nullable=True),
        sa.Column("video_url", sa.Text(), nullable=True),
        sa.Column("professional_url", sa.Text(), nullable=True),
    )
    # event_profile
    op.create_table(
        "event_profile",
        *_common_columns(),
        sa.Column("show_negotiable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("show_noncommercial", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("clothing_size", sa.Integer(), nullable=True),
        sa.Column("shoe_size", sa.Integer(), nullable=True),
        sa.Column("ethnicity", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("body_type", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("hair_color", sa.String(32), nullable=True),
        sa.Column("hair_length", sa.String(32), nullable=True),
        sa.Column("work_types", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("has_experience", sa.Boolean(), nullable=True),
        sa.Column("portfolio_url", sa.Text(), nullable=True),
        sa.Column("video_url", sa.Text(), nullable=True),
    )
    # general_profile
    op.create_table(
        "general_profile",
        *_common_columns(),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("physical_fitness", sa.String(16), nullable=True),
        sa.Column("work_types", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("has_experience", sa.Boolean(), nullable=True),
        sa.CheckConstraint(
            "physical_fitness IS NULL OR physical_fitness IN ('light','medium','heavy')",
            name="ck_general_profile_physical_fitness",
        ),
    )
    # admin_profile
    op.create_table(
        "admin_profile",
        *_common_columns(),
        sa.Column("education", sa.String(32), nullable=True),
        sa.Column("work_types", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("has_experience", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("admin_profile")
    op.drop_table("general_profile")
    op.drop_table("event_profile")
    op.drop_table("creative_profile")
```

- [ ] **Step 3: Добавить SQLAlchemy-модели в `db/models.py`**

После класса `ActorProfile` (строка 136) и перед классом `Channel` (строка 139) добавить:

```python
class UserCategorySubscription(Base):
    """Подписка пользователя на категорию. Multi-row, по одной строке на
    категорию. enabled=False = категория временно выключена в settings, но
    данные профиля сохранены."""

    __tablename__ = "user_category_subscription"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_user_category"),
    )


def _common_profile_columns():
    """Колонки, общие для всех 4 per-category profile-таблиц."""
    return {
        "id": mapped_column(BigInteger, primary_key=True, autoincrement=True),
        # user_id, completed_at, created_at, updated_at объявлены отдельно в каждом классе.
    }


class CreativeProfile(Base):
    """Анкета для категории «Творческие позиции» (актёры, модели).
    Поля идентичны старой ActorProfile + telegram_user."""

    __tablename__ = "creative_profile"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ready_for_travel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    actual_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    play_age_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    play_age_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    project_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    role_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    min_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    show_negotiable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_noncommercial: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_agency: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    height_cm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    clothing_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shoe_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ethnicity: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    body_type: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    hair_color: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    hair_length: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    has_experience: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    education: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    tax_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    eye_color: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    marks: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    skills_sport: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    skills_dance: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    skills_vocal: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    skills_instruments: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    portfolio_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    professional_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    vk_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    telegram_user: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class EventProfile(Base):
    """Анкета для категории «Event-персонал» (хостес, промо-модели, аниматоры)."""

    __tablename__ = "event_profile"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ready_for_travel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    actual_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    show_negotiable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_noncommercial: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    height_cm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    clothing_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shoe_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ethnicity: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    body_type: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    hair_color: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    hair_length: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    work_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    has_experience: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    tax_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    portfolio_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    vk_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    telegram_user: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class GeneralProfile(Base):
    """Анкета для категории «Разнорабочие» (хелперы, клининг, грузчики)."""

    __tablename__ = "general_profile"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ready_for_travel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    actual_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height_cm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    physical_fitness: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    work_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    has_experience: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    tax_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    vk_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    telegram_user: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AdminProfile(Base):
    """Анкета для категории «Администрирование» (операторы регистрации, супервайзеры)."""

    __tablename__ = "admin_profile"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ready_for_travel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    actual_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    education: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    work_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    has_experience: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    tax_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    vk_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    telegram_user: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

- [ ] **Step 4: Локально применить миграцию (smoke test)**

Команды требуют `DATABASE_URL`. Если есть локальный postgres — запустить:
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

Если нет — пропустить, миграция применится при деплое через `entrypoint.sh`.

- [ ] **Step 5: Коммит**

```bash
git add migrations/versions/0012_user_category_subscription.py \
        migrations/versions/0013_per_category_profiles.py \
        db/models.py
git commit -m "$(cat <<'EOF'
feat(db): per-category profile tables and subscriptions

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Pydantic-схемы и repository функции

**Files:**
- Modify: `api/schemas.py` (добавить 4 ProfileSchema + SubscriptionSchema + SuggestionsSchema)
- Modify: `db/repository.py` (добавить 7 функций для категорий и профилей)
- Create: `tests/test_schemas_per_category.py`
- Create: `tests/test_suggestions.py`

- [ ] **Step 1: Написать тесты Pydantic-схем (TDD)**

```python
# tests/test_schemas_per_category.py
"""Pydantic-валидация per-category схем."""
import pytest
from pydantic import ValidationError

from api.schemas import (
    AdminProfileSchema,
    CreativeProfileSchema,
    EventProfileSchema,
    GeneralProfileSchema,
)


def test_creative_profile_accepts_full_data():
    s = CreativeProfileSchema(
        full_name="Иван Петров",
        gender="male",
        city="Москва",
        actual_age=25,
        play_age_min=20,
        play_age_max=30,
        project_types=["advertising", "movie"],
        role_types=["main"],
        min_rate=5000,
        height_cm=180,
        ethnicity=["slavic"],
        body_type=["athletic"],
        hair_color="brown",
        hair_length="short",
        has_experience=True,
        education="higher",
        tax_status="self_employed",
        phone="+79991234567",
        telegram_user="ivan_p",
        email="ivan@example.com",
    )
    assert s.full_name == "Иван Петров"


def test_event_profile_work_types_validates():
    EventProfileSchema(work_types=["hostess", "animator"])
    with pytest.raises(ValidationError):
        EventProfileSchema(work_types=["invalid_value"])


def test_general_profile_physical_fitness_enum():
    GeneralProfileSchema(physical_fitness="medium")
    with pytest.raises(ValidationError):
        GeneralProfileSchema(physical_fitness="extra_heavy")


def test_general_profile_work_types_validates():
    GeneralProfileSchema(work_types=["helper", "loader"])
    with pytest.raises(ValidationError):
        GeneralProfileSchema(work_types=["actor"])


def test_admin_profile_work_types_validates():
    AdminProfileSchema(work_types=["registration_operator", "supervisor"])
    with pytest.raises(ValidationError):
        AdminProfileSchema(work_types=["hostess"])


def test_email_format_required():
    with pytest.raises(ValidationError):
        CreativeProfileSchema(email="not-an-email")


def test_all_optional_fields_can_be_omitted():
    """Draft-сохранение: PUT приходит с любым подмножеством полей."""
    CreativeProfileSchema()
    EventProfileSchema()
    GeneralProfileSchema()
    AdminProfileSchema()
```

- [ ] **Step 2: Запустить тесты — ожидать FAIL (схем ещё нет)**

```bash
pytest tests/test_schemas_per_category.py -v
```

Ожидание: ImportError или AttributeError (схем нет).

- [ ] **Step 3: Добавить Pydantic-схемы в `api/schemas.py`**

В конец файла добавить:

```python
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------- per-category profile schemas ----------

_VALID_EVENT_WORK_TYPES = {"hostess", "promo_model", "animator"}
_VALID_GENERAL_WORK_TYPES = {"helper", "cleaning", "loader"}
_VALID_ADMIN_WORK_TYPES = {"registration_operator", "supervisor"}
_VALID_PHYSICAL_FITNESS = {"light", "medium", "heavy"}


class _BaseProfileSchema(BaseModel):
    """Общие поля всех 4 категорий — все Optional на этапе draft."""

    full_name: Optional[str] = Field(default=None, max_length=128)
    gender: Optional[Literal["male", "female"]] = None
    city: Optional[str] = Field(default=None, max_length=64)
    ready_for_travel: bool = False
    actual_age: Optional[int] = Field(default=None, ge=0, le=120)
    min_rate: Optional[int] = Field(default=None, ge=0)
    tax_status: Optional[str] = Field(default=None, max_length=32)
    phone: Optional[str] = Field(default=None, max_length=32)
    vk_url: Optional[str] = None
    telegram_user: Optional[str] = Field(default=None, max_length=64)
    email: Optional[EmailStr] = None


class CreativeProfileSchema(_BaseProfileSchema):
    play_age_min: Optional[int] = Field(default=None, ge=0, le=120)
    play_age_max: Optional[int] = Field(default=None, ge=0, le=120)
    project_types: list[str] = Field(default_factory=list)
    role_types: list[str] = Field(default_factory=list)
    show_negotiable: bool = False
    show_noncommercial: bool = True
    show_agency: bool = True
    height_cm: Optional[int] = Field(default=None, ge=100, le=250)
    clothing_size: Optional[int] = Field(default=None, ge=20, le=80)
    shoe_size: Optional[int] = Field(default=None, ge=30, le=55)
    ethnicity: list[str] = Field(default_factory=list)
    body_type: list[str] = Field(default_factory=list)
    hair_color: Optional[str] = Field(default=None, max_length=32)
    hair_length: Optional[str] = Field(default=None, max_length=32)
    has_experience: Optional[bool] = None
    education: Optional[str] = Field(default=None, max_length=32)
    eye_color: Optional[str] = Field(default=None, max_length=32)
    marks: list[str] = Field(default_factory=list)
    skills_sport: list[str] = Field(default_factory=list)
    skills_dance: list[str] = Field(default_factory=list)
    skills_vocal: list[str] = Field(default_factory=list)
    skills_instruments: list[str] = Field(default_factory=list)
    portfolio_url: Optional[str] = None
    video_url: Optional[str] = None
    professional_url: Optional[str] = None


class EventProfileSchema(_BaseProfileSchema):
    show_negotiable: bool = False
    show_noncommercial: bool = True
    height_cm: Optional[int] = Field(default=None, ge=100, le=250)
    clothing_size: Optional[int] = Field(default=None, ge=20, le=80)
    shoe_size: Optional[int] = Field(default=None, ge=30, le=55)
    ethnicity: list[str] = Field(default_factory=list)
    body_type: list[str] = Field(default_factory=list)
    hair_color: Optional[str] = Field(default=None, max_length=32)
    hair_length: Optional[str] = Field(default=None, max_length=32)
    work_types: list[str] = Field(default_factory=list)
    has_experience: Optional[bool] = None
    portfolio_url: Optional[str] = None
    video_url: Optional[str] = None

    @field_validator("work_types")
    @classmethod
    def _validate_work_types(cls, v: list[str]) -> list[str]:
        invalid = set(v) - _VALID_EVENT_WORK_TYPES
        if invalid:
            raise ValueError(f"Недопустимые work_types: {invalid}")
        return v


class GeneralProfileSchema(_BaseProfileSchema):
    height_cm: Optional[int] = Field(default=None, ge=100, le=250)
    physical_fitness: Optional[str] = Field(default=None, max_length=16)
    work_types: list[str] = Field(default_factory=list)
    has_experience: Optional[bool] = None

    @field_validator("physical_fitness")
    @classmethod
    def _validate_physical_fitness(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _VALID_PHYSICAL_FITNESS:
            raise ValueError(f"physical_fitness must be one of {_VALID_PHYSICAL_FITNESS}")
        return v

    @field_validator("work_types")
    @classmethod
    def _validate_work_types(cls, v: list[str]) -> list[str]:
        invalid = set(v) - _VALID_GENERAL_WORK_TYPES
        if invalid:
            raise ValueError(f"Недопустимые work_types: {invalid}")
        return v


class AdminProfileSchema(_BaseProfileSchema):
    education: Optional[str] = Field(default=None, max_length=32)
    work_types: list[str] = Field(default_factory=list)
    has_experience: Optional[bool] = None

    @field_validator("work_types")
    @classmethod
    def _validate_work_types(cls, v: list[str]) -> list[str]:
        invalid = set(v) - _VALID_ADMIN_WORK_TYPES
        if invalid:
            raise ValueError(f"Недопустимые work_types: {invalid}")
        return v


# ---------- subscriptions ----------

CategoryCode = Literal["creative", "event", "general", "admin"]


class SubscriptionSchema(BaseModel):
    category: CategoryCode
    enabled: bool
    profile_completed: bool


class SubscriptionsCreateRequest(BaseModel):
    categories: list[CategoryCode]


class SubscriptionPatchRequest(BaseModel):
    enabled: bool


# ---------- suggestions ----------

class SuggestionsResponse(BaseModel):
    """Ответ /api/profile/suggestions: для каждого канонического ключа —
    список ранее введённых юзером значений (dedupe + sort by updated_at desc)."""

    suggestions: dict[str, list]
```

- [ ] **Step 4: Запустить тесты — ожидать PASS**

```bash
pytest tests/test_schemas_per_category.py -v
```

- [ ] **Step 5: Написать тест функции `_collect_suggestions` (TDD)**

```python
# tests/test_suggestions.py
"""Чистая логика сбора autocomplete-suggestions из per-category профилей."""
from datetime import datetime, timezone

from db.repository import _collect_suggestions


def test_collect_suggestions_dedupes_values():
    """Если одно и то же значение лежит в двух профилях — отдаём один раз."""
    profiles = {
        "creative": {"city": "Москва", "phone": "+79991111111", "updated_at": datetime(2026, 5, 1, tzinfo=timezone.utc)},
        "event": {"city": "Москва", "phone": "+79992222222", "updated_at": datetime(2026, 5, 2, tzinfo=timezone.utc)},
    }
    result = _collect_suggestions(profiles)
    assert result["city"] == ["Москва"]
    assert sorted(result["phone"]) == ["+79991111111", "+79992222222"]


def test_collect_suggestions_orders_by_updated_at_desc():
    """Свежие значения первыми."""
    profiles = {
        "creative": {"city": "Москва", "updated_at": datetime(2026, 5, 1, tzinfo=timezone.utc)},
        "event": {"city": "СПб", "updated_at": datetime(2026, 5, 5, tzinfo=timezone.utc)},
    }
    result = _collect_suggestions(profiles)
    assert result["city"] == ["СПб", "Москва"]


def test_collect_suggestions_skips_none_and_empty():
    profiles = {
        "creative": {"city": None, "phone": "", "updated_at": datetime(2026, 5, 1, tzinfo=timezone.utc)},
        "event": {"city": "Москва", "phone": "+79991111111", "updated_at": datetime(2026, 5, 2, tzinfo=timezone.utc)},
    }
    result = _collect_suggestions(profiles)
    assert result["city"] == ["Москва"]
    assert result["phone"] == ["+79991111111"]


def test_collect_suggestions_skips_arrays_unless_canonical():
    """list[str] поля (project_types, work_types) не подсказываются — только скаляры."""
    profiles = {
        "creative": {"project_types": ["advertising"], "city": "Москва",
                     "updated_at": datetime(2026, 5, 1, tzinfo=timezone.utc)},
    }
    result = _collect_suggestions(profiles)
    assert "project_types" not in result
    assert result["city"] == ["Москва"]


def test_collect_suggestions_empty_profiles():
    assert _collect_suggestions({}) == {}
```

- [ ] **Step 6: Запустить тесты — ожидать FAIL**

```bash
pytest tests/test_suggestions.py -v
```

- [ ] **Step 7: Реализовать repository функции в `db/repository.py`**

В конец файла добавить:

```python
from db.models import (
    AdminProfile,
    CreativeProfile,
    EventProfile,
    GeneralProfile,
    UserCategorySubscription,
)


# ---------- CATEGORIES ----------

CATEGORY_TO_MODEL = {
    "creative": CreativeProfile,
    "event": EventProfile,
    "general": GeneralProfile,
    "admin": AdminProfile,
}

# Канонические скалярные поля, которые шарятся между категориями
# и попадают в /api/profile/suggestions. multi-select поля и
# category-специфичные (project_types, work_types) — НЕ включаем.
_SUGGESTION_FIELDS = {
    "full_name", "gender", "city", "actual_age", "min_rate",
    "height_cm", "clothing_size", "shoe_size",
    "hair_color", "hair_length",
    "tax_status", "education", "phone", "vk_url",
    "telegram_user", "email", "portfolio_url", "video_url",
}


async def get_subscriptions(user_id: int) -> list[dict]:
    """Список подписок юзера + флаг profile_completed для каждой."""
    async with AsyncSessionLocal() as session:
        subs_res = await session.execute(
            select(UserCategorySubscription).where(UserCategorySubscription.user_id == user_id)
        )
        subs = list(subs_res.scalars().all())
        if not subs:
            return []
        # Для каждой категории — узнать completed_at профиля
        result = []
        for sub in subs:
            model = CATEGORY_TO_MODEL[sub.category]
            prof_res = await session.execute(
                select(model.completed_at).where(model.user_id == user_id)
            )
            completed_at = prof_res.scalar_one_or_none()
            result.append({
                "category": sub.category,
                "enabled": sub.enabled,
                "profile_completed": completed_at is not None,
            })
        return result


async def set_subscriptions(user_id: int, categories: list[str]) -> list[dict]:
    """Создать строки подписок для каждой категории. Идемпотентно."""
    async with AsyncSessionLocal() as session:
        await upsert_user_in_session(session, user_id)
        for cat in categories:
            stmt = (
                pg_insert(UserCategorySubscription)
                .values(user_id=user_id, category=cat, enabled=True)
                .on_conflict_do_nothing(index_elements=["user_id", "category"])
            )
            await session.execute(stmt)
        await session.commit()
    return await get_subscriptions(user_id)


async def toggle_subscription(user_id: int, category: str, enabled: bool) -> bool:
    """Сменить enabled-флаг. Возвращает True если строка существовала."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(UserCategorySubscription).where(
                UserCategorySubscription.user_id == user_id,
                UserCategorySubscription.category == category,
            )
        )
        sub = res.scalar_one_or_none()
        if sub is None:
            return False
        sub.enabled = enabled
        await session.commit()
        return True


# ---------- PER-CATEGORY PROFILES ----------

async def get_category_profile(user_id: int, category: str) -> Optional[dict]:
    """Вернуть профиль категории как dict (или None)."""
    model = CATEGORY_TO_MODEL.get(category)
    if model is None:
        return None
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(model).where(model.user_id == user_id))
        row = res.scalar_one_or_none()
        if row is None:
            return None
        return _profile_row_to_dict(row)


def _profile_row_to_dict(row) -> dict:
    """Сериализация профиль-row в dict (без SQLAlchemy-метаданных)."""
    return {
        c.name: getattr(row, c.name)
        for c in row.__table__.columns
    }


async def upsert_category_profile(
    user_id: int, category: str, data: dict
) -> Optional[dict]:
    """Draft-сохранение полей в профиль категории. Создаёт или обновляет."""
    model = CATEGORY_TO_MODEL.get(category)
    if model is None:
        return None
    async with AsyncSessionLocal() as session:
        await upsert_user_in_session(session, user_id)
        res = await session.execute(select(model).where(model.user_id == user_id))
        row = res.scalar_one_or_none()
        if row is None:
            row = model(user_id=user_id)
            session.add(row)
        for k, v in data.items():
            if hasattr(row, k) and k not in {"id", "user_id", "created_at", "updated_at", "completed_at"}:
                setattr(row, k, v)
        await session.commit()
        await session.refresh(row)
        return _profile_row_to_dict(row)


async def complete_category_profile(
    user_id: int, category: str
) -> tuple[Optional[dict], bool]:
    """Поставить completed_at=now(). Возвращает (profile_dict, was_first_time)."""
    model = CATEGORY_TO_MODEL.get(category)
    if model is None:
        return None, False
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(model).where(model.user_id == user_id))
        row = res.scalar_one_or_none()
        if row is None:
            return None, False
        was_first_time = row.completed_at is None
        row.completed_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(row)
        return _profile_row_to_dict(row), was_first_time


# ---------- SUGGESTIONS ----------

def _collect_suggestions(profiles: dict[str, dict]) -> dict[str, list]:
    """Собрать autocomplete-suggestions из профилей юзера.

    profiles: {category_code: {field: value, 'updated_at': dt}}
    Возвращает {field: [values...]} — только канонические скалярные поля,
    dedupe, сортировка по updated_at источника DESC.
    """
    by_field: dict[str, list[tuple[datetime, object]]] = {}
    for cat, data in profiles.items():
        updated = data.get("updated_at")
        if updated is None:
            continue
        for field, value in data.items():
            if field not in _SUGGESTION_FIELDS:
                continue
            if value is None or value == "":
                continue
            by_field.setdefault(field, []).append((updated, value))

    result: dict[str, list] = {}
    for field, items in by_field.items():
        items.sort(key=lambda x: x[0], reverse=True)
        seen = set()
        deduped: list = []
        for _, val in items:
            if val in seen:
                continue
            seen.add(val)
            deduped.append(val)
        result[field] = deduped
    return result


async def get_suggestions(user_id: int) -> dict[str, list]:
    """Собрать suggestions из всех 4 профилей юзера."""
    profiles: dict[str, dict] = {}
    async with AsyncSessionLocal() as session:
        for cat, model in CATEGORY_TO_MODEL.items():
            res = await session.execute(select(model).where(model.user_id == user_id))
            row = res.scalar_one_or_none()
            if row is not None:
                profiles[cat] = _profile_row_to_dict(row)
    return _collect_suggestions(profiles)
```

- [ ] **Step 8: Запустить тесты — ожидать PASS**

```bash
pytest tests/test_schemas_per_category.py tests/test_suggestions.py -v
```

- [ ] **Step 9: Коммит**

```bash
git add api/schemas.py db/repository.py \
        tests/test_schemas_per_category.py tests/test_suggestions.py
git commit -m "$(cat <<'EOF'
feat(api): pydantic schemas + repository for per-category profiles

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: API эндпоинты

**Files:**
- Modify: `api/main.py` (расширить `/api/me`, добавить 6 новых эндпоинтов)

- [ ] **Step 1: Расширить `GET /api/me` и добавить новые эндпоинты**

Заменить функцию `me` (строки 76-83) и добавить новые роуты в конец файла:

```python
from api.schemas import (
    AdminProfileSchema,
    CreativeProfileSchema,
    EventProfileSchema,
    GeneralProfileSchema,
    SubscriptionPatchRequest,
    SubscriptionsCreateRequest,
    SuggestionsResponse,
)
from db import repository as repo

CATEGORY_TO_SCHEMA = {
    "creative": CreativeProfileSchema,
    "event": EventProfileSchema,
    "general": GeneralProfileSchema,
    "admin": AdminProfileSchema,
}


@app.get("/api/me")
async def me(user: TelegramUser = Depends(current_user)) -> dict:
    """Кто я + админ ли + список подписок на категории."""
    subscriptions = await repo.get_subscriptions(user.id)
    return {
        "user_id": user.id,
        "username": user.username,
        "is_admin": is_admin_user(user),
        "subscriptions": subscriptions,
    }


@app.post("/api/subscriptions")
async def create_subscriptions(
    body: SubscriptionsCreateRequest,
    user: TelegramUser = Depends(current_user),
) -> dict:
    """Создать строки подписки. Идемпотентно. Возвращает обновлённый список."""
    subs = await repo.set_subscriptions(user.id, body.categories)
    return {"subscriptions": subs}


@app.patch("/api/subscriptions/{category}")
async def patch_subscription(
    category: str,
    body: SubscriptionPatchRequest,
    user: TelegramUser = Depends(current_user),
) -> dict:
    """Поменять enabled на категории."""
    if category not in CATEGORY_TO_SCHEMA:
        raise HTTPException(400, "Unknown category")
    ok = await repo.toggle_subscription(user.id, category, body.enabled)
    if not ok:
        raise HTTPException(404, "Subscription not found")
    return {"ok": True}


@app.get("/api/profile/{category}")
async def get_category_profile_endpoint(
    category: str,
    user: TelegramUser = Depends(current_user),
) -> dict:
    """Профиль категории или пустой объект если не создан."""
    if category not in CATEGORY_TO_SCHEMA:
        raise HTTPException(400, "Unknown category")
    p = await repo.get_category_profile(user.id, category)
    return p or {"user_id": user.id, "category": category}


@app.put("/api/profile/{category}")
async def upsert_category_profile_endpoint(
    category: str,
    body: dict,
    user: TelegramUser = Depends(current_user),
) -> dict:
    """Draft-сохранение. Валидация Pydantic, но без проверки completeness."""
    if category not in CATEGORY_TO_SCHEMA:
        raise HTTPException(400, "Unknown category")
    schema_cls = CATEGORY_TO_SCHEMA[category]
    validated = schema_cls.model_validate(body)
    p = await repo.upsert_category_profile(
        user.id, category, validated.model_dump(exclude_unset=True)
    )
    return p or {}


@app.post("/api/profile/{category}/complete")
async def complete_category_profile_endpoint(
    category: str,
    user: TelegramUser = Depends(current_user),
) -> dict:
    """Финальное завершение анкеты категории — шлёт уведомление в бот."""
    if category not in CATEGORY_TO_SCHEMA:
        raise HTTPException(400, "Unknown category")
    p, was_first_time = await repo.complete_category_profile(user.id, category)
    if p is None:
        raise HTTPException(400, "Profile not found")
    text = FIRST_COMPLETION_MESSAGE if was_first_time else RECOMPLETION_MESSAGE
    await _notify_user(user.id, text)
    return p


@app.get("/api/profile/suggestions", response_model=SuggestionsResponse)
async def profile_suggestions(
    user: TelegramUser = Depends(current_user),
) -> SuggestionsResponse:
    """Autocomplete-подсказки: значения, ранее введённые юзером в одноимённых полях
    других своих профилей."""
    suggestions = await repo.get_suggestions(user.id)
    return SuggestionsResponse(suggestions=suggestions)
```

- [ ] **Step 2: Локально запустить uvicorn и проверить эндпоинты**

```bash
# В терминале 1: запустить FastAPI
DATABASE_URL=postgresql+asyncpg://... uvicorn api.main:app --reload --port 8000

# В терминале 2: проверить health
curl http://localhost:8000/api/health
# {"status":"ok"}
```

Если `DATABASE_URL` не настроен — пропустить, проверим на этапе деплоя.

- [ ] **Step 3: Коммит**

```bash
git add api/main.py
git commit -m "$(cat <<'EOF'
feat(api): per-category profile endpoints + subscriptions + suggestions

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Frontend — state machine + опросник + меню категорий

**Files:**
- Modify: `webapp/src/types.ts` (добавить типы Subscription, ProfileCategory)
- Modify: `webapp/src/api.ts` (добавить функции под новые эндпоинты)
- Create: `webapp/src/components/CategorySurveyScreen.tsx`
- Create: `webapp/src/components/CategoryMenuScreen.tsx`
- Modify: `webapp/src/App.tsx` (state machine)

- [ ] **Step 1: Добавить типы в `webapp/src/types.ts`**

В конец файла:

```typescript
export type CategoryCode = "creative" | "event" | "general" | "admin";

export interface Subscription {
  category: CategoryCode;
  enabled: boolean;
  profile_completed: boolean;
}

export interface MeResponse {
  user_id: number;
  username: string | null;
  is_admin: boolean;
  subscriptions: Subscription[];
}

export const CATEGORY_LABELS: Record<CategoryCode, string> = {
  creative: "Творческие позиции",
  event: "Event-персонал",
  general: "Разнорабочие",
  admin: "Администрирование",
};

export const CATEGORY_DESCRIPTIONS: Record<CategoryCode, string> = {
  creative: "Актёры, модели",
  event: "Хостес, промо-модели, аниматоры",
  general: "Хелперы, клининг, грузчики",
  admin: "Операторы регистрации, супервайзеры",
};
```

- [ ] **Step 2: Добавить API-функции в `webapp/src/api.ts`**

В конец файла:

```typescript
import type { CategoryCode, MeResponse, Subscription } from "./types";

export async function getMe(): Promise<MeResponse> {
  return apiGet("/api/me");
}

export async function createSubscriptions(categories: CategoryCode[]): Promise<{ subscriptions: Subscription[] }> {
  return apiPost("/api/subscriptions", { categories });
}

export async function patchSubscription(category: CategoryCode, enabled: boolean): Promise<{ ok: boolean }> {
  return apiPatch(`/api/subscriptions/${category}`, { enabled });
}

export async function getCategoryProfile<T = any>(category: CategoryCode): Promise<T> {
  return apiGet(`/api/profile/${category}`);
}

export async function putCategoryProfile<T = any>(category: CategoryCode, data: any): Promise<T> {
  return apiPut(`/api/profile/${category}`, data);
}

export async function completeCategoryProfile<T = any>(category: CategoryCode): Promise<T> {
  return apiPost(`/api/profile/${category}/complete`, {});
}

export async function getSuggestions(): Promise<{ suggestions: Record<string, any[]> }> {
  return apiGet("/api/profile/suggestions");
}
```

(Если в `api.ts` ещё нет `apiPatch` или `apiPut` — добавить аналогично существующим `apiGet`/`apiPost`.)

- [ ] **Step 3: Создать `CategorySurveyScreen.tsx`**

```typescript
// webapp/src/components/CategorySurveyScreen.tsx
import { useState } from "react";
import { createSubscriptions } from "../api";
import type { CategoryCode } from "../types";
import { CATEGORY_LABELS, CATEGORY_DESCRIPTIONS } from "../types";

const ALL_CATEGORIES: CategoryCode[] = ["creative", "event", "general", "admin"];

interface Props {
  onDone: () => void;
  excludeCategories?: CategoryCode[];
}

export function CategorySurveyScreen({ onDone, excludeCategories = [] }: Props) {
  const [selected, setSelected] = useState<Set<CategoryCode>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const visible = ALL_CATEGORIES.filter((c) => !excludeCategories.includes(c));

  const toggle = (c: CategoryCode) => {
    const next = new Set(selected);
    if (next.has(c)) next.delete(c); else next.add(c);
    setSelected(next);
  };

  const submit = async () => {
    if (selected.size === 0) return;
    setSubmitting(true);
    try {
      await createSubscriptions(Array.from(selected));
      onDone();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-bold">Какие направления интересуют?</h1>
      <p className="text-gray-600">Выбери одно или несколько — для каждого заполнишь свою анкету.</p>
      <div className="space-y-3">
        {visible.map((c) => (
          <label
            key={c}
            className={`block p-4 border rounded-lg cursor-pointer ${
              selected.has(c) ? "border-blue-500 bg-blue-50" : "border-gray-300"
            }`}
          >
            <input
              type="checkbox"
              checked={selected.has(c)}
              onChange={() => toggle(c)}
              className="mr-3"
            />
            <span className="font-semibold">{CATEGORY_LABELS[c]}</span>
            <div className="text-sm text-gray-600 ml-7">{CATEGORY_DESCRIPTIONS[c]}</div>
          </label>
        ))}
      </div>
      <button
        onClick={submit}
        disabled={selected.size === 0 || submitting}
        className="w-full py-3 bg-blue-500 text-white rounded-lg disabled:opacity-50"
      >
        {submitting ? "Сохраняем..." : "Продолжить"}
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Создать `CategoryMenuScreen.tsx`**

```typescript
// webapp/src/components/CategoryMenuScreen.tsx
import type { CategoryCode, Subscription } from "../types";
import { CATEGORY_LABELS } from "../types";

interface Props {
  subscriptions: Subscription[];
  onOpenForm: (c: CategoryCode) => void;
  onAddCategory: () => void;
  onSettings: () => void;
}

export function CategoryMenuScreen({ subscriptions, onOpenForm, onAddCategory, onSettings }: Props) {
  const enabled = subscriptions.filter((s) => s.enabled);
  const canAdd = subscriptions.length < 4;

  return (
    <div className="p-6 space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Мои направления</h1>
        <button onClick={onSettings} className="text-2xl">⚙️</button>
      </div>
      <div className="space-y-3">
        {enabled.map((s) => (
          <button
            key={s.category}
            onClick={() => onOpenForm(s.category)}
            className="w-full p-4 border rounded-lg flex justify-between items-center hover:bg-gray-50"
          >
            <span className="font-semibold">{CATEGORY_LABELS[s.category]}</span>
            <span className="text-sm">
              {s.profile_completed ? "✅ Заполнена" : "⚠️ Не заполнена"}
            </span>
          </button>
        ))}
      </div>
      {canAdd && (
        <button
          onClick={onAddCategory}
          className="w-full py-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-600"
        >
          + Добавить категорию
        </button>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Обновить `App.tsx` с state machine**

Заменить содержимое `App.tsx` на (или добавить state machine, если файл сложный):

```typescript
import { useEffect, useState } from "react";
import { CategoryMenuScreen } from "./components/CategoryMenuScreen";
import { CategorySurveyScreen } from "./components/CategorySurveyScreen";
import { getMe } from "./api";
import type { CategoryCode, Subscription } from "./types";

type Screen =
  | { kind: "loading" }
  | { kind: "survey" }
  | { kind: "menu" }
  | { kind: "form"; category: CategoryCode }
  | { kind: "settings" }
  | { kind: "addCategory" };

export default function App() {
  const [screen, setScreen] = useState<Screen>({ kind: "loading" });
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);

  const refreshMe = async () => {
    const me = await getMe();
    setSubscriptions(me.subscriptions);
    if (me.subscriptions.length === 0) {
      setScreen({ kind: "survey" });
    } else {
      setScreen({ kind: "menu" });
    }
  };

  useEffect(() => {
    refreshMe();
  }, []);

  if (screen.kind === "loading") {
    return <div className="p-6">Загрузка…</div>;
  }

  if (screen.kind === "survey") {
    return <CategorySurveyScreen onDone={refreshMe} />;
  }

  if (screen.kind === "menu") {
    return (
      <CategoryMenuScreen
        subscriptions={subscriptions}
        onOpenForm={(c) => setScreen({ kind: "form", category: c })}
        onAddCategory={() => setScreen({ kind: "addCategory" })}
        onSettings={() => setScreen({ kind: "settings" })}
      />
    );
  }

  if (screen.kind === "addCategory") {
    return (
      <CategorySurveyScreen
        excludeCategories={subscriptions.map((s) => s.category)}
        onDone={refreshMe}
      />
    );
  }

  if (screen.kind === "form") {
    // Заглушка — наполнится в Task 5
    return (
      <div className="p-6">
        <button onClick={() => setScreen({ kind: "menu" })}>← Назад</button>
        <h2 className="text-xl mt-4">Форма категории {screen.category}</h2>
        <p className="text-gray-500">Будет реализована в Task 5.</p>
      </div>
    );
  }

  if (screen.kind === "settings") {
    // Заглушка — наполнится в Task 6
    return (
      <div className="p-6">
        <button onClick={() => setScreen({ kind: "menu" })}>← Назад</button>
        <h2 className="text-xl mt-4">Настройки</h2>
        <p className="text-gray-500">Будут реализованы в Task 6.</p>
      </div>
    );
  }

  return null;
}
```

- [ ] **Step 6: Локально запустить vite dev server и проверить**

```bash
cd webapp && npm run dev
# Открыть в браузере, убедиться что после клиринга подписок видим экран survey,
# можно выбрать категории, перейти в меню.
```

- [ ] **Step 7: Коммит**

```bash
git add webapp/src/types.ts webapp/src/api.ts \
        webapp/src/App.tsx \
        webapp/src/components/CategorySurveyScreen.tsx \
        webapp/src/components/CategoryMenuScreen.tsx
git commit -m "$(cat <<'EOF'
feat(webapp): category survey + main menu navigation

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Frontend — 4 формы категорий + shared field components

**Files:**
- Create: `webapp/src/fields/TextFieldWithAutocomplete.tsx`
- Create: `webapp/src/fields/NumberFieldWithAutocomplete.tsx`
- Create: `webapp/src/fields/SelectField.tsx`
- Create: `webapp/src/fields/MultiSelectField.tsx`
- Create: `webapp/src/contexts/SuggestionsContext.tsx`
- Create: `webapp/src/forms/CreativeForm.tsx` (рефакторинг существующего `components/steps.tsx` под одну категорию)
- Create: `webapp/src/forms/EventForm.tsx`
- Create: `webapp/src/forms/GeneralForm.tsx`
- Create: `webapp/src/forms/AdminForm.tsx`
- Modify: `webapp/src/App.tsx` (заменить заглушку form)

- [ ] **Step 1: SuggestionsContext + Provider**

```typescript
// webapp/src/contexts/SuggestionsContext.tsx
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { getSuggestions } from "../api";

type Suggestions = Record<string, any[]>;

const SuggestionsContext = createContext<Suggestions>({});

export function SuggestionsProvider({ children }: { children: ReactNode }) {
  const [suggestions, setSuggestions] = useState<Suggestions>({});

  useEffect(() => {
    getSuggestions().then((r) => setSuggestions(r.suggestions));
  }, []);

  return (
    <SuggestionsContext.Provider value={suggestions}>
      {children}
    </SuggestionsContext.Provider>
  );
}

export function useFieldSuggestions(field: string): any[] {
  const all = useContext(SuggestionsContext);
  return all[field] ?? [];
}
```

- [ ] **Step 2: TextFieldWithAutocomplete**

```typescript
// webapp/src/fields/TextFieldWithAutocomplete.tsx
import { useState } from "react";
import { useFieldSuggestions } from "../contexts/SuggestionsContext";

interface Props {
  field: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: "text" | "email" | "tel" | "url";
}

export function TextFieldWithAutocomplete({ field, label, value, onChange, placeholder, type = "text" }: Props) {
  const suggestions = useFieldSuggestions(field).filter(
    (s): s is string => typeof s === "string"
  );
  const [focused, setFocused] = useState(false);
  const filtered = suggestions.filter((s) => !value || s.toLowerCase().includes(value.toLowerCase())).slice(0, 5);

  return (
    <label className="block space-y-1">
      <span className="text-sm font-medium">{label}</span>
      <div className="relative">
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 150)}
          placeholder={placeholder}
          className="w-full p-2 border rounded"
        />
        {focused && filtered.length > 0 && (
          <ul className="absolute z-10 w-full bg-white border rounded mt-1 shadow">
            {filtered.map((s) => (
              <li
                key={s}
                onMouseDown={(e) => {
                  e.preventDefault();
                  onChange(s);
                }}
                className="p-2 hover:bg-gray-100 cursor-pointer text-sm"
              >
                {s}
              </li>
            ))}
          </ul>
        )}
      </div>
    </label>
  );
}
```

- [ ] **Step 3: NumberFieldWithAutocomplete**

```typescript
// webapp/src/fields/NumberFieldWithAutocomplete.tsx
import { useFieldSuggestions } from "../contexts/SuggestionsContext";

interface Props {
  field: string;
  label: string;
  value: number | null;
  onChange: (v: number | null) => void;
  min?: number;
  max?: number;
}

export function NumberFieldWithAutocomplete({ field, label, value, onChange, min, max }: Props) {
  const suggestions = useFieldSuggestions(field).filter(
    (s): s is number => typeof s === "number"
  );

  return (
    <label className="block space-y-1">
      <span className="text-sm font-medium">{label}</span>
      <input
        type="number"
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
        min={min}
        max={max}
        className="w-full p-2 border rounded"
      />
      {suggestions.length > 0 && value === null && (
        <div className="flex gap-2 mt-1">
          {suggestions.slice(0, 3).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onChange(s)}
              className="text-xs px-2 py-1 border rounded text-gray-600 hover:bg-gray-100"
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </label>
  );
}
```

- [ ] **Step 4: SelectField и MultiSelectField (без autocomplete — это enum)**

```typescript
// webapp/src/fields/SelectField.tsx
interface Option { value: string; label: string; }
interface Props {
  label: string;
  value: string | null;
  onChange: (v: string | null) => void;
  options: Option[];
}
export function SelectField({ label, value, onChange, options }: Props) {
  return (
    <label className="block space-y-1">
      <span className="text-sm font-medium">{label}</span>
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value || null)}
        className="w-full p-2 border rounded"
      >
        <option value="">—</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </label>
  );
}
```

```typescript
// webapp/src/fields/MultiSelectField.tsx
interface Option { value: string; label: string; }
interface Props {
  label: string;
  value: string[];
  onChange: (v: string[]) => void;
  options: Option[];
}
export function MultiSelectField({ label, value, onChange, options }: Props) {
  const toggle = (v: string) => {
    onChange(value.includes(v) ? value.filter((x) => x !== v) : [...value, v]);
  };
  return (
    <fieldset className="space-y-1">
      <legend className="text-sm font-medium">{label}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button
            key={o.value}
            type="button"
            onClick={() => toggle(o.value)}
            className={`px-3 py-1 border rounded text-sm ${
              value.includes(o.value) ? "bg-blue-500 text-white border-blue-500" : ""
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}
```

- [ ] **Step 5: CreativeForm — рефакторинг существующего steps.tsx под новый эндпоинт**

`webapp/src/forms/CreativeForm.tsx` создаётся как многошаговая форма (Step1-6 как было), но:
- Загружает данные через `getCategoryProfile("creative")` вместо `/api/profile`.
- Сохраняет через `putCategoryProfile("creative", data)`.
- Финализирует через `completeCategoryProfile("creative")`.
- Использует `<TextFieldWithAutocomplete field="city" ...>` вместо обычных `<input>` для общих полей.

Подробная имплементация — см. существующий `webapp/src/components/steps.tsx`, перенести каждый Step1-6 как отдельный мини-компонент внутри CreativeForm. Текстовые/числовые поля общих ключей (full_name, city, phone, telegram_user, email, vk_url, height_cm, clothing_size, shoe_size, actual_age, min_rate, hair_color, hair_length, education, tax_status, portfolio_url, video_url) — обернуть в `<TextFieldWithAutocomplete>` / `<NumberFieldWithAutocomplete>`. Остальные (project_types, role_types, ethnicity, body_type, marks, skills_*) — `<MultiSelectField>`. Категориально-специфичные (eye_color и т.п.) — обычный `<SelectField>`.

```typescript
// webapp/src/forms/CreativeForm.tsx (skeleton)
import { useEffect, useState } from "react";
import { completeCategoryProfile, getCategoryProfile, putCategoryProfile } from "../api";
import { TextFieldWithAutocomplete } from "../fields/TextFieldWithAutocomplete";
import { NumberFieldWithAutocomplete } from "../fields/NumberFieldWithAutocomplete";
// ... остальные импорты

interface Props { onDone: () => void; }

export function CreativeForm({ onDone }: Props) {
  const [step, setStep] = useState(1);
  const [data, setData] = useState<any>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCategoryProfile("creative").then((p) => {
      setData(p);
      setLoading(false);
    });
  }, []);

  const update = (patch: any) => {
    const next = { ...data, ...patch };
    setData(next);
    putCategoryProfile("creative", next);  // draft-save (debounce можно добавить)
  };

  const finish = async () => {
    await completeCategoryProfile("creative");
    onDone();
  };

  if (loading) return <div className="p-6">Загрузка…</div>;

  // 6 шагов с кнопкой «Далее» / «Назад» / финальной «Сохранить»
  // ... (полная имплементация повторяет существующий steps.tsx,
  //     с заменой <input> на <TextFieldWithAutocomplete field="city" ...>)
}
```

(Если файл steps.tsx большой и его сложно отрефакторить по этому плану — задача может быть разбита на под-таски: «реализовать Step1», «Step2» и т.д. Контроллер плана может это сделать на лету.)

- [ ] **Step 6: EventForm — упрощённая версия**

```typescript
// webapp/src/forms/EventForm.tsx
import { useEffect, useState } from "react";
import { completeCategoryProfile, getCategoryProfile, putCategoryProfile } from "../api";
import { TextFieldWithAutocomplete } from "../fields/TextFieldWithAutocomplete";
import { NumberFieldWithAutocomplete } from "../fields/NumberFieldWithAutocomplete";
import { MultiSelectField } from "../fields/MultiSelectField";
import { SelectField } from "../fields/SelectField";

interface Props { onDone: () => void; }

const WORK_TYPES = [
  { value: "hostess", label: "Хостес" },
  { value: "promo_model", label: "Промо-модель" },
  { value: "animator", label: "Аниматор" },
];

export function EventForm({ onDone }: Props) {
  const [data, setData] = useState<any>({ work_types: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCategoryProfile("event").then((p) => {
      setData(p);
      setLoading(false);
    });
  }, []);

  const update = (patch: any) => {
    const next = { ...data, ...patch };
    setData(next);
    putCategoryProfile("event", next);
  };

  if (loading) return <div className="p-6">Загрузка…</div>;

  return (
    <div className="p-6 space-y-4">
      <h2 className="text-xl font-bold">Анкета — Event-персонал</h2>
      <TextFieldWithAutocomplete field="full_name" label="ФИО" value={data.full_name ?? ""} onChange={(v) => update({ full_name: v })} />
      <TextFieldWithAutocomplete field="city" label="Город" value={data.city ?? ""} onChange={(v) => update({ city: v })} />
      <NumberFieldWithAutocomplete field="actual_age" label="Возраст" value={data.actual_age ?? null} onChange={(v) => update({ actual_age: v })} min={14} max={80} />
      <NumberFieldWithAutocomplete field="height_cm" label="Рост, см" value={data.height_cm ?? null} onChange={(v) => update({ height_cm: v })} min={120} max={220} />
      <NumberFieldWithAutocomplete field="min_rate" label="Минимальная ставка, ₽" value={data.min_rate ?? null} onChange={(v) => update({ min_rate: v })} min={0} />
      <MultiSelectField label="Типы готовых работ" value={data.work_types ?? []} onChange={(v) => update({ work_types: v })} options={WORK_TYPES} />
      <SelectField label="Опыт работы" value={data.has_experience === true ? "yes" : data.has_experience === false ? "no" : null} onChange={(v) => update({ has_experience: v === "yes" ? true : v === "no" ? false : null })} options={[{ value: "yes", label: "Есть" }, { value: "no", label: "Нет" }]} />
      <TextFieldWithAutocomplete field="phone" label="Телефон" value={data.phone ?? ""} onChange={(v) => update({ phone: v })} type="tel" />
      <TextFieldWithAutocomplete field="telegram_user" label="Telegram username" value={data.telegram_user ?? ""} onChange={(v) => update({ telegram_user: v })} />
      <TextFieldWithAutocomplete field="vk_url" label="VK" value={data.vk_url ?? ""} onChange={(v) => update({ vk_url: v })} type="url" />
      <TextFieldWithAutocomplete field="email" label="Email" value={data.email ?? ""} onChange={(v) => update({ email: v })} type="email" />
      <TextFieldWithAutocomplete field="portfolio_url" label="Фото-портфолио" value={data.portfolio_url ?? ""} onChange={(v) => update({ portfolio_url: v })} type="url" />
      <TextFieldWithAutocomplete field="video_url" label="Видео-портфолио" value={data.video_url ?? ""} onChange={(v) => update({ video_url: v })} type="url" />
      <button
        onClick={async () => { await completeCategoryProfile("event"); onDone(); }}
        className="w-full py-3 bg-blue-500 text-white rounded-lg"
      >
        Сохранить анкету
      </button>
    </div>
  );
}
```

- [ ] **Step 7: GeneralForm**

```typescript
// webapp/src/forms/GeneralForm.tsx
import { useEffect, useState } from "react";
import { completeCategoryProfile, getCategoryProfile, putCategoryProfile } from "../api";
import { TextFieldWithAutocomplete } from "../fields/TextFieldWithAutocomplete";
import { NumberFieldWithAutocomplete } from "../fields/NumberFieldWithAutocomplete";
import { MultiSelectField } from "../fields/MultiSelectField";
import { SelectField } from "../fields/SelectField";

interface Props { onDone: () => void; }

const WORK_TYPES = [
  { value: "helper", label: "Хелпер" },
  { value: "cleaning", label: "Клининг" },
  { value: "loader", label: "Грузчик" },
];
const FITNESS = [
  { value: "light", label: "До 5 кг" },
  { value: "medium", label: "5–20 кг" },
  { value: "heavy", label: "20+ кг" },
];

export function GeneralForm({ onDone }: Props) {
  const [data, setData] = useState<any>({ work_types: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCategoryProfile("general").then((p) => {
      setData(p);
      setLoading(false);
    });
  }, []);

  const update = (patch: any) => {
    const next = { ...data, ...patch };
    setData(next);
    putCategoryProfile("general", next);
  };

  if (loading) return <div className="p-6">Загрузка…</div>;

  return (
    <div className="p-6 space-y-4">
      <h2 className="text-xl font-bold">Анкета — Разнорабочие</h2>
      <TextFieldWithAutocomplete field="full_name" label="ФИО" value={data.full_name ?? ""} onChange={(v) => update({ full_name: v })} />
      <TextFieldWithAutocomplete field="city" label="Город" value={data.city ?? ""} onChange={(v) => update({ city: v })} />
      <NumberFieldWithAutocomplete field="actual_age" label="Возраст" value={data.actual_age ?? null} onChange={(v) => update({ actual_age: v })} min={14} max={80} />
      <NumberFieldWithAutocomplete field="height_cm" label="Рост, см (опц.)" value={data.height_cm ?? null} onChange={(v) => update({ height_cm: v })} min={120} max={220} />
      <NumberFieldWithAutocomplete field="min_rate" label="Минимальная ставка, ₽" value={data.min_rate ?? null} onChange={(v) => update({ min_rate: v })} min={0} />
      <SelectField label="Физ. подготовка (опц.)" value={data.physical_fitness ?? null} onChange={(v) => update({ physical_fitness: v })} options={FITNESS} />
      <MultiSelectField label="Типы готовых работ" value={data.work_types ?? []} onChange={(v) => update({ work_types: v })} options={WORK_TYPES} />
      <SelectField label="Опыт работы" value={data.has_experience === true ? "yes" : data.has_experience === false ? "no" : null} onChange={(v) => update({ has_experience: v === "yes" ? true : v === "no" ? false : null })} options={[{ value: "yes", label: "Есть" }, { value: "no", label: "Нет" }]} />
      <TextFieldWithAutocomplete field="phone" label="Телефон" value={data.phone ?? ""} onChange={(v) => update({ phone: v })} type="tel" />
      <TextFieldWithAutocomplete field="telegram_user" label="Telegram" value={data.telegram_user ?? ""} onChange={(v) => update({ telegram_user: v })} />
      <TextFieldWithAutocomplete field="vk_url" label="VK" value={data.vk_url ?? ""} onChange={(v) => update({ vk_url: v })} type="url" />
      <TextFieldWithAutocomplete field="email" label="Email" value={data.email ?? ""} onChange={(v) => update({ email: v })} type="email" />
      <button
        onClick={async () => { await completeCategoryProfile("general"); onDone(); }}
        className="w-full py-3 bg-blue-500 text-white rounded-lg"
      >
        Сохранить анкету
      </button>
    </div>
  );
}
```

- [ ] **Step 8: AdminForm**

```typescript
// webapp/src/forms/AdminForm.tsx
import { useEffect, useState } from "react";
import { completeCategoryProfile, getCategoryProfile, putCategoryProfile } from "../api";
import { TextFieldWithAutocomplete } from "../fields/TextFieldWithAutocomplete";
import { NumberFieldWithAutocomplete } from "../fields/NumberFieldWithAutocomplete";
import { MultiSelectField } from "../fields/MultiSelectField";
import { SelectField } from "../fields/SelectField";

interface Props { onDone: () => void; }

const WORK_TYPES = [
  { value: "registration_operator", label: "Оператор регистрации" },
  { value: "supervisor", label: "Супервайзер" },
];

export function AdminForm({ onDone }: Props) {
  const [data, setData] = useState<any>({ work_types: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCategoryProfile("admin").then((p) => {
      setData(p);
      setLoading(false);
    });
  }, []);

  const update = (patch: any) => {
    const next = { ...data, ...patch };
    setData(next);
    putCategoryProfile("admin", next);
  };

  if (loading) return <div className="p-6">Загрузка…</div>;

  return (
    <div className="p-6 space-y-4">
      <h2 className="text-xl font-bold">Анкета — Администрирование</h2>
      <TextFieldWithAutocomplete field="full_name" label="ФИО" value={data.full_name ?? ""} onChange={(v) => update({ full_name: v })} />
      <TextFieldWithAutocomplete field="city" label="Город" value={data.city ?? ""} onChange={(v) => update({ city: v })} />
      <NumberFieldWithAutocomplete field="actual_age" label="Возраст" value={data.actual_age ?? null} onChange={(v) => update({ actual_age: v })} min={14} max={80} />
      <NumberFieldWithAutocomplete field="min_rate" label="Минимальная ставка, ₽" value={data.min_rate ?? null} onChange={(v) => update({ min_rate: v })} min={0} />
      <TextFieldWithAutocomplete field="education" label="Образование" value={data.education ?? ""} onChange={(v) => update({ education: v })} />
      <MultiSelectField label="Типы готовых работ" value={data.work_types ?? []} onChange={(v) => update({ work_types: v })} options={WORK_TYPES} />
      <SelectField label="Опыт работы" value={data.has_experience === true ? "yes" : data.has_experience === false ? "no" : null} onChange={(v) => update({ has_experience: v === "yes" ? true : v === "no" ? false : null })} options={[{ value: "yes", label: "Есть" }, { value: "no", label: "Нет" }]} />
      <TextFieldWithAutocomplete field="phone" label="Телефон" value={data.phone ?? ""} onChange={(v) => update({ phone: v })} type="tel" />
      <TextFieldWithAutocomplete field="telegram_user" label="Telegram" value={data.telegram_user ?? ""} onChange={(v) => update({ telegram_user: v })} />
      <TextFieldWithAutocomplete field="vk_url" label="VK" value={data.vk_url ?? ""} onChange={(v) => update({ vk_url: v })} type="url" />
      <TextFieldWithAutocomplete field="email" label="Email" value={data.email ?? ""} onChange={(v) => update({ email: v })} type="email" />
      <button
        onClick={async () => { await completeCategoryProfile("admin"); onDone(); }}
        className="w-full py-3 bg-blue-500 text-white rounded-lg"
      >
        Сохранить анкету
      </button>
    </div>
  );
}
```

- [ ] **Step 9: Подключить формы в `App.tsx`**

Заменить заглушку `screen.kind === "form"` на реальные формы, обернув всё в `<SuggestionsProvider>`:

```typescript
import { SuggestionsProvider } from "./contexts/SuggestionsContext";
import { CreativeForm } from "./forms/CreativeForm";
import { EventForm } from "./forms/EventForm";
import { GeneralForm } from "./forms/GeneralForm";
import { AdminForm } from "./forms/AdminForm";

// внутри App component, обернуть весь return в <SuggestionsProvider>
// и заменить блок form:

if (screen.kind === "form") {
  const formProps = { onDone: refreshMe };
  const Form = {
    creative: CreativeForm,
    event: EventForm,
    general: GeneralForm,
    admin: AdminForm,
  }[screen.category];
  return (
    <div>
      <button onClick={() => setScreen({ kind: "menu" })} className="m-4">← Назад</button>
      <Form {...formProps} />
    </div>
  );
}
```

И `<SuggestionsProvider>` оборачивает корень, например:

```typescript
return (
  <SuggestionsProvider>
    {/* существующий switch по screen */}
  </SuggestionsProvider>
);
```

- [ ] **Step 10: Локально проверить все 4 формы**

```bash
cd webapp && npm run dev
# Заполнить ФИО+Город в Event, переключиться на Admin — autocomplete должен подсказать.
```

- [ ] **Step 11: Коммит**

```bash
git add webapp/src/contexts/SuggestionsContext.tsx \
        webapp/src/fields/ \
        webapp/src/forms/ \
        webapp/src/App.tsx
git commit -m "$(cat <<'EOF'
feat(webapp): per-category forms + autocomplete fields

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Frontend — SettingsScreen + cleanup

**Files:**
- Create: `webapp/src/components/SettingsScreen.tsx`
- Modify: `webapp/src/App.tsx` (заменить заглушку settings)

- [ ] **Step 1: Создать SettingsScreen**

```typescript
// webapp/src/components/SettingsScreen.tsx
import { patchSubscription } from "../api";
import type { CategoryCode, Subscription } from "../types";
import { CATEGORY_LABELS, CATEGORY_DESCRIPTIONS } from "../types";

const ALL: CategoryCode[] = ["creative", "event", "general", "admin"];

interface Props {
  subscriptions: Subscription[];
  onChange: () => Promise<void> | void;
  onEditForm: (c: CategoryCode) => void;
  onBack: () => void;
}

export function SettingsScreen({ subscriptions, onChange, onEditForm, onBack }: Props) {
  const subMap = new Map(subscriptions.map((s) => [s.category, s]));

  const toggle = async (c: CategoryCode, enabled: boolean) => {
    const sub = subMap.get(c);
    if (!sub) return;  // не подписан — игнорим
    await patchSubscription(c, enabled);
    await onChange();
  };

  return (
    <div className="p-6 space-y-4">
      <button onClick={onBack} className="text-blue-500">← Назад</button>
      <h1 className="text-2xl font-bold">Настройки</h1>
      <div className="space-y-3">
        {ALL.map((c) => {
          const sub = subMap.get(c);
          const subscribed = sub !== undefined;
          return (
            <div key={c} className={`p-4 border rounded-lg ${subscribed ? "" : "opacity-50"}`}>
              <div className="flex justify-between items-center">
                <div>
                  <div className="font-semibold">{CATEGORY_LABELS[c]}</div>
                  <div className="text-sm text-gray-600">{CATEGORY_DESCRIPTIONS[c]}</div>
                </div>
                {subscribed && (
                  <input
                    type="checkbox"
                    checked={sub!.enabled}
                    onChange={(e) => toggle(c, e.target.checked)}
                    className="w-6 h-6"
                  />
                )}
              </div>
              {subscribed && (
                <button
                  onClick={() => onEditForm(c)}
                  className="mt-2 text-sm text-blue-500"
                >
                  Изменить анкету
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Подключить в App.tsx**

Заменить заглушку `screen.kind === "settings"` на:

```typescript
if (screen.kind === "settings") {
  return (
    <SettingsScreen
      subscriptions={subscriptions}
      onChange={refreshMe}
      onEditForm={(c) => setScreen({ kind: "form", category: c })}
      onBack={() => setScreen({ kind: "menu" })}
    />
  );
}
```

- [ ] **Step 3: Проверить локально**

```bash
cd webapp && npm run dev
# В меню нажать ⚙️ → settings; toggle категории → меню обновляется (выкл. категория не показывается);
# Открыть «Изменить анкету» — переходит в форму.
```

- [ ] **Step 4: Коммит**

```bash
git add webapp/src/components/SettingsScreen.tsx webapp/src/App.tsx
git commit -m "$(cat <<'EOF'
feat(webapp): settings screen with per-category enable toggle

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Cutover — переключение матчера и обновление GREETING

**Files:**
- Modify: `db/matching.py` (читать из `creative_profile` вместо `actor_profile`)
- Modify: `bot/handlers.py` (обновить GREETING)
- Modify: `userbot/client.py` (если матчер вызывается оттуда — проверить)
- Modify: `tests/test_matching.py` (если есть и адаптировать)

- [ ] **Step 1: Обновить GREETING в bot/handlers.py**

Найти константу `GREETING` (~строка 30-50 в `bot/handlers.py`) и обновить две строки:

```python
GREETING = (
    "<b>Добро пожаловать в Model Promo Agency!</b> 👋\n\n"
    "Мы рады видеть тебя в нашей команде. Это не просто бот, а мощный "
    "агрегатор вакансий: мы в реальном времени анализируем огромную сеть "
    "каналов и агентств, чтобы ты получал уведомления о кастингах и работе "
    "самым первым! 🚀\n\n"
    "<b>Кого мы ищем?</b>\n"
    "У нас открыт набор на следующие направления:\n\n"
    "🛠 <b>Разнорабочие:</b> хелперы, клининг, грузчики.\n"
    "🎉 <b>Event-персонал:</b> хостес, промо-модели, аниматоры.\n"
    "📸 <b>Творческие позиции:</b> актёры и модели.\n"
    "💻 <b>Администрирование:</b> операторы регистрации, супервайзеры.\n\n"
    "<b>Как начать зарабатывать?</b>\n"
    "Чтобы не пропускать лучшие предложения и настроить уведомления, "
    "открой Mini App рядом с полем ввода и заполни короткую анкету — "
    "там можно выбрать интересующие тебя категории."
)
```

- [ ] **Step 2: Переключить матчинг с actor_profile на creative_profile**

В `db/matching.py` найти место, где загружается `ActorProfile`:

```python
# было
from db.models import ActorProfile
# ...
profile_res = await session.execute(
    select(ActorProfile).where(ActorProfile.user_id == user_id, ActorProfile.completed_at.is_not(None))
)
```

заменить на:

```python
from db.models import CreativeProfile, UserCategorySubscription
# ...
profile_res = await session.execute(
    select(CreativeProfile)
    .join(UserCategorySubscription, UserCategorySubscription.user_id == CreativeProfile.user_id)
    .where(
        CreativeProfile.user_id == user_id,
        CreativeProfile.completed_at.is_not(None),
        UserCategorySubscription.category == "creative",
        UserCategorySubscription.enabled.is_(True),
    )
)
```

Если в `matching.py` есть итерация по списку всех завершённых анкет (например, `notify_users` flow) — переключить аналогично: matching работает только для подписки `creative`+enabled+completed.

- [ ] **Step 3: Адаптировать существующие тесты матчинга**

Если в `tests/test_matching.py` создаются `ActorProfile`-фикстуры — заменить на `CreativeProfile`. Если файл не запускается без БД (как `test_notification_format.py`) — это пре-existing issue, не блокирует.

- [ ] **Step 4: Проверить локально что бот всё ещё стартует**

```bash
# Smoke-test — что нет import-ошибок
python -c "from bot import handlers; from db import matching; from api import main"
```

- [ ] **Step 5: Коммит**

```bash
git add bot/handlers.py db/matching.py tests/test_matching.py
git commit -m "$(cat <<'EOF'
feat(cutover): matcher reads creative_profile + greeting updated

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 6: Push branch + Open PR**

```bash
git push -u origin feat/mini-app-categories
gh pr create --title "feat: mini-app categories + per-category profiles + autocomplete" --body "$(cat <<'EOF'
## Summary
- 4 категории (creative/event/general/admin), опросник при первом открытии Mini App
- 4 независимые таблицы профилей + `user_category_subscription` (multi-row + enable toggle)
- Autocomplete-подсказки между одноимёнными полями разных категорий
- SettingsScreen для вкл/выкл категорий и редактирования анкет
- GREETING обновлён (аниматоры, супервайзеры)
- Матчинг переключён с `actor_profile` на `creative_profile` (другие категории — отдельный спек)
- Старые юзеры начинают анкету заново; `actor_profile` остаётся read-only

## Test plan
- [ ] Локальный pytest (test_schemas_per_category, test_suggestions) — проходит
- [ ] После деплоя: открыть Mini App → видим опрос
- [ ] Выбрать 2 категории, заполнить одну, переключиться на вторую — autocomplete предлагает значения
- [ ] Зайти в settings, выключить категорию — пропадает из меню
- [ ] Включить обратно — появляется с заполненными данными
- [ ] Старый юзер с заполненным `actor_profile.completed_at` — видит опрос (новые подписки пусты)
- [ ] Бот шлёт уведомления только тем, у кого `subscription.creative.enabled=TRUE AND creative_profile.completed_at IS NOT NULL`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-review notes

- **Spec coverage**: все 7 этапов из спека отражены в Tasks 1-7. Subscription enabled/disabled (Settings) — Task 6. Cutover — Task 7. Autocomplete — Tasks 2 (бэк) + 5 (фронт).
- **Тесты под формы**: целенаправленно нет — UI-тесты в этом проекте не настроены, smoke-test через ручной запуск vite.
- **Фронт без TDD**: pragmatic — TDD для UI без e2e-фреймворка не работает.
- **Объём Task 5 большой** (4 формы) — допустимо разбить на под-таски при выполнении (контроллер плана может делать sub-dispatch).
- **CreativeForm**: подробная имплементация не дана пошагово, потому что это рефакторинг существующего `steps.tsx` (большой файл) — описана стратегия. Если subagent затруднится — может задать вопрос или escalate.
- **Race-fix дедупа**: НЕ в этом плане. Отдельным спеком после.
