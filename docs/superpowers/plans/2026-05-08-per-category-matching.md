# Per-Category Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Расширить LLM-extract и матчер так, чтобы юзеры с подписками `event` / `general` / `admin` получали уведомления по релевантным вакансиям (сейчас только `creative` работает).

**Architecture:** LLM получает расширенный SYSTEM_PROMPT и возвращает `PostExtraction.category` (доминирующая категория поста) + `VacancyExtraction.{category, work_types}`. Миграция 0016 добавляет колонки `messages.category`, `vacancies.category`, `vacancies.work_types[]` с бэкфиллом существующих creating-постов в `category='creative'`. Матчер `find_matching_vacancies` диспатчит по `effective_cat = vacancy.category or post.category` в одну из четырёх per-category функций; каждая загружает свою профиль-таблицу с фильтром по `UserCategorySubscription`.

**Tech Stack:** Pydantic 2 + SQLAlchemy 2.0 async + Alembic + PostgreSQL + pytest + OpenAI-compatible LLM.

**Spec:** `docs/superpowers/specs/2026-05-08-per-category-matching-design.md`.

---

## Task 1: Pydantic-схемы + reference data + валидация

**Files:**
- Modify: `D:\Documents\Claude\Projects\model_pro\models\schemas.py` (расширить PostExtraction, VacancyExtraction)
- Modify: `D:\Documents\Claude\Projects\model_pro\api\reference_data.py` (добавить 3 новых справочника)
- Modify: `D:\Documents\Claude\Projects\model_pro\api\schemas.py` (свести валидаторы work_types на справочники)
- Test: `D:\Documents\Claude\Projects\model_pro\tests\test_schemas_per_category.py` (расширить)

- [ ] **Step 1: Расширить `models/schemas.py`**

Заменить содержимое `models/schemas.py` целиком на:

```python
"""Pydantic-схемы для извлечённых данных и пользовательских фильтров."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

CategoryCode = Literal["creative", "event", "general", "admin"]


class VacancyExtraction(BaseModel):
    """Одна вакансия (роль) внутри поста."""

    role_types: list[str] = []
    work_types: list[str] = []
    category: Optional[CategoryCode] = None
    gender: Optional[Literal["male", "female"]] = None
    age_min: Optional[int] = Field(None, ge=0, le=120)
    age_max: Optional[int] = Field(None, ge=0, le=120)
    rate: Optional[int] = Field(None, ge=0)
    ethnicity: list[str] = []
    height_min: Optional[int] = Field(None, ge=50, le=250)
    height_max: Optional[int] = Field(None, ge=50, le=250)
    body_type: list[str] = []
    hair_color: list[str] = []
    hair_length: list[str] = []
    description: Optional[str] = None
    role_label: Optional[str] = None


class PostExtraction(BaseModel):
    """Структура, которую LLM извлекает из объявления о кастинге.

    `category` — доминирующая категория поста (creative/event/general/admin),
    `Vacancy.category` опционально перекрывает её для гибрид-постов.
    """

    is_casting: bool = False
    category: Optional[CategoryCode] = None
    project_types: list[str] = []
    city: Optional[str] = None
    summary: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    vacancies: list[VacancyExtraction] = []


class UserFilter(BaseModel):
    """Устаревшая модель текстового фильтра. Сейчас матчинг идёт по
    actor_profiles (см. db.matching), но схема остаётся для совместимости
    с историческими данными в таблице filters.
    """

    user_id: int
    target_gender: Optional[Literal["male", "female"]] = None
    min_age: Optional[int] = Field(None, ge=0, le=120)
    max_age: Optional[int] = Field(None, ge=0, le=120)
    category: Optional[str] = None
    min_confidence: float = Field(0.5, ge=0.0, le=1.0)
```

(Изменения: новый `CategoryCode`, добавлены поля `category`/`work_types` в `VacancyExtraction`, добавлено поле `category` в `PostExtraction`.)

- [ ] **Step 2: Добавить новые справочники в `api/reference_data.py`**

Найти секцию `SKILLS_INSTRUMENTS = _items([...])` (~строка 158-167). Сразу после неё добавить:

```python
WORK_TYPES_EVENT = _items([
    ("hostess", "Хостес"),
    ("promo_model", "Промо-модель"),
    ("animator", "Аниматор"),
])

WORK_TYPES_GENERAL = _items([
    ("helper", "Хелпер"),
    ("cleaning", "Клининг"),
    ("loader", "Грузчик"),
])

WORK_TYPES_ADMIN = _items([
    ("registration_operator", "Оператор регистрации"),
    ("supervisor", "Супервайзер"),
])
```

Затем найти функцию `all_refs()` (около строки 170) и расширить return-словарь, добавив 3 новые ключа в конец перед закрывающей `}`:

```python
def all_refs() -> dict[str, list[RefItem]]:
    """Полный словарь справочников для отдачи фронту одним запросом."""
    return {
        "genders": GENDERS,
        "project_types": PROJECT_TYPES,
        "role_types": ROLE_TYPES,
        "ethnicity": ETHNICITY,
        "body_type": BODY_TYPE,
        "hair_colors": HAIR_COLORS,
        "hair_lengths": HAIR_LENGTHS,
        "education": EDUCATION,
        "tax_status": TAX_STATUS,
        "eye_colors": EYE_COLORS,
        "marks": MARKS,
        "skills_sport": SKILLS_SPORT,
        "skills_dance": SKILLS_DANCE,
        "skills_vocal": SKILLS_VOCAL,
        "skills_instruments": SKILLS_INSTRUMENTS,
        "work_types_event": WORK_TYPES_EVENT,
        "work_types_general": WORK_TYPES_GENERAL,
        "work_types_admin": WORK_TYPES_ADMIN,
    }
```

`all_codes()` подхватит новые справочники автоматически (она итерирует по `all_refs()`).

- [ ] **Step 3: Заменить hardcoded валидаторы в `api/schemas.py` на справочники**

Открыть `api/schemas.py`. Найти константы `_VALID_EVENT_WORK_TYPES`, `_VALID_GENERAL_WORK_TYPES`, `_VALID_ADMIN_WORK_TYPES`. Они сейчас захардкожены как `set[str]`. Заменить эти три объявления на использование `all_codes()`:

```python
# Заменить блок с тремя константами _VALID_*_WORK_TYPES на:
from api.reference_data import all_codes as _all_codes

_REF_CODES = _all_codes()
_VALID_EVENT_WORK_TYPES = _REF_CODES["work_types_event"]
_VALID_GENERAL_WORK_TYPES = _REF_CODES["work_types_general"]
_VALID_ADMIN_WORK_TYPES = _REF_CODES["work_types_admin"]
```

Это держит whitelist в одном месте — в `reference_data.py`. Pydantic-валидаторы в `EventProfileSchema`/`GeneralProfileSchema`/`AdminProfileSchema` продолжат работать.

(Если в файле уже есть `from api.reference_data import all_codes` — переиспользовать без второго импорта.)

- [ ] **Step 4: Расширить тесты в `tests/test_schemas_per_category.py`**

Открыть `tests/test_schemas_per_category.py`. В конец добавить тесты на новые поля LLM-схем:

```python
# В начало файла добавить (если уже есть PostExtraction/VacancyExtraction импорт — расширить):
from models.schemas import PostExtraction, VacancyExtraction


def test_post_extraction_accepts_category():
    p = PostExtraction(is_casting=True, category="event", confidence=0.8)
    assert p.category == "event"


def test_post_extraction_rejects_invalid_category():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PostExtraction(is_casting=True, category="invalid")


def test_post_extraction_category_optional():
    p = PostExtraction(is_casting=False)
    assert p.category is None


def test_vacancy_extraction_accepts_work_types_and_category():
    v = VacancyExtraction(
        work_types=["hostess", "animator"],
        category="event",
        gender="female",
    )
    assert v.work_types == ["hostess", "animator"]
    assert v.category == "event"


def test_vacancy_extraction_defaults_empty_work_types():
    v = VacancyExtraction()
    assert v.work_types == []
    assert v.category is None
```

- [ ] **Step 5: Запустить тесты — должны пройти**

```bash
pytest tests/test_schemas_per_category.py -v
```

Expected: все тесты, включая новые 5, проходят.

- [ ] **Step 6: Smoke-test that all_refs работает**

```bash
python -c "from api.reference_data import all_refs, all_codes; refs = all_refs(); print('keys:', sorted(refs.keys())[-3:]); codes = all_codes(); print('event:', codes['work_types_event']); print('general:', codes['work_types_general']); print('admin:', codes['work_types_admin'])"
```

Expected output:
```
keys: ['work_types_admin', 'work_types_event', 'work_types_general']
event: {'hostess', 'promo_model', 'animator'}
general: {'helper', 'cleaning', 'loader'}
admin: {'registration_operator', 'supervisor'}
```

(Порядок элементов в set может быть другим — главное что три кода в каждом).

- [ ] **Step 7: Commit**

```bash
git add models/schemas.py api/reference_data.py api/schemas.py tests/test_schemas_per_category.py
git commit -m "$(cat <<'EOF'
feat(schemas): per-category fields in LLM extraction + work_types refs

- PostExtraction.category and VacancyExtraction.{category,work_types}
- WORK_TYPES_EVENT/GENERAL/ADMIN reference data
- api/schemas.py work_types validators sourced from reference_data

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Миграция 0016 + ORM модели

**Files:**
- Create: `D:\Documents\Claude\Projects\model_pro\migrations\versions\0016_per_category_vacancies.py`
- Modify: `D:\Documents\Claude\Projects\model_pro\db\models.py` (Message + Vacancy)

- [ ] **Step 1: Создать миграцию 0016**

Создать `migrations/versions/0016_per_category_vacancies.py` с содержимым:

```python
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
```

- [ ] **Step 2: Проверить что миграция компилируется**

```bash
python -m py_compile migrations/versions/0016_per_category_vacancies.py
```

Expected: 0 errors.

- [ ] **Step 3: Расширить Message в `db/models.py`**

Открыть `D:\Documents\Claude\Projects\model_pro\db\models.py`. Найти класс `Message` (около строки 415, после блока с text_hash и canonical_message_id). После поля `category: Mapped[Optional[str]]` (или после `confidence`/`text_hash` — где есть «хвост от старой схемы»):

В существующем `Message` уже есть поле `category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)` — это **legacy** колонка. Не путать с новой.

Решение: добавить **новую** колонку с другим именем `post_category` чтобы не конфликтовать со старой? Нет — в спеке мы именуем `messages.category`. Старая колонка не используется (см. комментарий «Хвост от старой модели»). Но миграция 0016 добавляет ещё один `category` → конфликт имён.

**Действие:** проверить есть ли уже `category` в schema. Если есть в legacy — её **переименовать** в `legacy_category` в миграции 0016 ДО добавления нового `category`. Расширить миграцию upgrade с переименования:

Дополнить `upgrade()` в миграции 0016, **в самое начало**:

```python
    # Старая колонка category (legacy) переименовывается, чтобы не конфликтовать
    # с новой category (per-category matching). Старые данные в этой колонке
    # не используются кодом.
    op.alter_column("messages", "category", new_column_name="legacy_category")
```

И в `downgrade()` обратное переименование (после восстановления других дропов):

```python
    op.alter_column("messages", "legacy_category", new_column_name="category")
```

Однако! Сначала надо проверить, есть ли старая колонка category в Message. Прочитать `db/models.py` вокруг класса Message.

Если **старая колонка `category` уже есть** в модели Message — переименовать её там в `legacy_category` тоже. Если **нет** (была удалена раньше) — никакого alter_column в миграции не нужно, использовать чистый `add_column("category")`.

Implementer должен **прочитать `db/models.py` и проверить**. Если в Message нет поля `category` — пропустить шаг переименования. Если есть — добавить переименование в миграцию.

- [ ] **Step 4: Добавить новые поля в Message и Vacancy**

Открыть `db/models.py`. Если в Message есть legacy `category` — переименовать атрибут на `legacy_category` (строкой `category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)` → `legacy_category: Mapped[Optional[str]] = ...`).

Затем в Message добавить новое поле `category` (не путать с legacy):

```python
    # Per-category matching: доминирующая категория поста, определённая LLM.
    category: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
```

Добавить рядом с существующими полями (например после `confidence` или после `text_hash`/`canonical_message_id`).

В Vacancy (около строки 472+, после полей `description`, `role_label`):

```python
    # Per-category matching: override для гибрид-постов (если категория этой
    # вакансии отличается от доминирующей категории поста). NULL = inherit.
    category: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    # Коды work_types для event/general/admin вакансий (для creative — пусто).
    work_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
```

`String`, `ARRAY`, `Text`, `Optional`, `Mapped`, `mapped_column` — уже импортированы.

- [ ] **Step 5: Smoke-test модели**

```bash
python -c "from db.models import Message, Vacancy; print('Message.category:', hasattr(Message, 'category'), 'Vacancy.category:', hasattr(Vacancy, 'category'), 'Vacancy.work_types:', hasattr(Vacancy, 'work_types'))"
```

Expected: все три `True`.

- [ ] **Step 6: Commit**

```bash
git add migrations/versions/0016_per_category_vacancies.py db/models.py
git commit -m "$(cat <<'EOF'
feat(db): migration 0016 — messages.category + vacancies.category/work_types

Adds per-category matching columns. Backfills existing casting messages
with category='creative'. Renames legacy messages.category column to
legacy_category if present (was unused tail from old schema).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: LLM normalize + SYSTEM_PROMPT

**Files:**
- Modify: `D:\Documents\Claude\Projects\model_pro\llm\base.py` (расширить SYSTEM_PROMPT)
- Modify: `D:\Documents\Claude\Projects\model_pro\llm\normalize.py` (нормализация work_types/category)
- Modify: `D:\Documents\Claude\Projects\model_pro\tests\test_normalize.py` (расширить)

- [ ] **Step 1: Расширить SYSTEM_PROMPT в `llm/base.py`**

Заменить значение константы `SYSTEM_PROMPT` (строки 14-69) на:

```python
SYSTEM_PROMPT = """Ты разбираешь объявления о работе и кастингах из
Telegram-каналов. Из присланного сообщения нужно извлечь параметры
поиска и вернуть СТРОГО JSON-объект без markdown-обёрток.

Категория поста (post.category) — доминирующее направление:
- "creative"  — кастинги в кино/сериалы/рекламу/театр/модельные проекты;
                роли: актёры, модели, фотомодели, дикторы, ведущие, танцоры.
- "event"     — мероприятия, презентации, корпоративы;
                роли: хостес, промо-модели, аниматоры.
- "general"   — разнорабочие на event/съёмки;
                роли: хелпер, клининг, грузчик.
- "admin"     — администрирование на мероприятиях;
                роли: оператор регистрации, супервайзер.

Структура поста:
{
  "is_casting": bool,                    // это объявление о работе?
                                         // false для рекламы услуг, обучения и т.п.
  "category": str|null,                  // доминирующая категория:
                                         // "creative"|"event"|"general"|"admin"
                                         // null если не входит в список
                                         // или is_casting=false
  "project_types": [str],                // только для creative; подмножество кодов:
                                         // kino_serial, advertising, model_projects,
                                         // show_reality, voice_dub, theater
                                         // Для event/general/admin — пустой массив.
  "city": str|null,                      // город на русском
  "summary": str|null,                   // краткое описание поста до 30 слов
  "confidence": float,                   // 0.0-1.0, твоя уверенность
  "vacancies": [                         // список ролей; пустой если is_casting=false
    {
      "role_types": [str],               // ТОЛЬКО для creative. Подмножество кодов:
                                         // main, supporting, episode, massovka,
                                         // groupovka, dubler, kaskader, model,
                                         // photo_model, promo_model, tv_host, diktor,
                                         // dancer, ballerina, gymnast, vocalist, musician.
                                         // Для event/general/admin — пустой массив.
      "work_types": [str],               // ТОЛЬКО для event/general/admin:
                                         // - event: hostess, promo_model, animator
                                         // - general: helper, cleaning, loader
                                         // - admin: registration_operator, supervisor
                                         // Для creative — пустой массив.
      "category": str|null,              // null = наследовать post.category;
                                         // указывать только если эта роль явно из
                                         // другой категории чем доминирующая
                                         // (редкие гибрид-посты).
      "gender": "male"|"female"|null,    // кого ищут на эту роль
      "age_min": int|null,               // нижний возраст; для одного значения 25 — age_min=age_max=25
      "age_max": int|null,
      "rate": int|null,                  // ставка в рублях за смену; диапазон — нижняя граница
      "ethnicity": [str],                 // подмножество кодов внешности (только creative/event):
                                          // slavic, european, caucasian, asian,
                                          // central_asian, african, arab, latin,
                                          // mixed, other.
                                          // Пустой массив если не указано или
                                          // не релевантно (general/admin).
      "height_min": int|null,             // рост в см, нижняя граница
      "height_max": int|null,             // рост в см, верхняя граница;
                                          // одно значение "рост 180" → height_min=height_max=180
      "body_type": [str],                 // подмножество кодов телосложения
                                          // (только creative/event):
                                          // slim, athletic, normal, plus_size, muscular.
      "hair_color": [str],                // подмножество цветов волос (creative/event):
                                          // black, dark_brown, brown, light_brown,
                                          // blond, red, grey, dyed.
      "hair_length": [str],               // подмножество кодов длины волос (creative/event):
                                          // bald, very_short, short, medium, long, very_long.
      "description": str|null,           // фрагмент поста об этой роли
      "role_label": str|null             // короткое имя роли как в посте: "Мама", "Сын", "Прохожий", "Хостес"
    }
  ]
}

ВАЖНО:
- Если в посте описана одна роль — vacancies массив длины 1.
- Если описаны несколько разных ролей с разными условиями (возрастом,
  гонораром, полом, внешностью, ростом, типом работы) — заводи на каждую отдельную
  запись в vacancies.
- Если is_casting=false — vacancies должно быть пустым массивом, category=null.
- Для creative-вакансий заполняй role_types, work_types оставь пустым.
- Для event/general/admin вакансий заполняй work_types, role_types оставь пустым.
- Никаких комментариев, только JSON.
"""
```

- [ ] **Step 2: Расширить `llm/normalize.py`**

Заменить функцию `_normalize_vacancy` (строки 58-67) на:

```python
def _normalize_vacancy(v: VacancyExtraction) -> VacancyExtraction:
    # work_types: справочник зависит от категории. Если категория не задана
    # на уровне вакансии (типичный случай) — нормализовать по объединению
    # всех трёх whitelist'ов; если LLM вернул мусор, он отфильтруется
    # на следующем уровне (per-category matcher).
    work_types_normalized = (
        _normalize_list("work_types_event", v.work_types)
        + _normalize_list("work_types_general", v.work_types)
        + _normalize_list("work_types_admin", v.work_types)
    )
    # Дедупликация
    seen: set[str] = set()
    work_types_dedup: list[str] = []
    for code in work_types_normalized:
        if code not in seen:
            seen.add(code)
            work_types_dedup.append(code)

    return v.model_copy(
        update={
            "role_types": _normalize_list("role_types", v.role_types),
            "work_types": work_types_dedup,
            "ethnicity": _normalize_list("ethnicity", v.ethnicity),
            "body_type": _normalize_list("body_type", v.body_type),
            "hair_color": _normalize_list("hair_colors", v.hair_color),
            "hair_length": _normalize_list("hair_lengths", v.hair_length),
        }
    )
```

`v.category` оставляем как есть (Pydantic-литерал уже валидирует на этапе парсинга).

- [ ] **Step 3: Расширить `tests/test_normalize.py`**

В `tests/test_normalize.py` найти существующие тесты. Добавить новые (в конец файла):

```python
def test_normalize_event_work_types():
    p = PostExtraction(
        is_casting=True,
        category="event",
        vacancies=[
            VacancyExtraction(work_types=["hostess", "animator"]),
        ],
    )
    out = normalize_extracted(p)
    assert out.vacancies[0].work_types == ["hostess", "animator"]


def test_normalize_general_work_types():
    p = PostExtraction(
        is_casting=True,
        category="general",
        vacancies=[
            VacancyExtraction(work_types=["loader", "cleaning"]),
        ],
    )
    out = normalize_extracted(p)
    assert sorted(out.vacancies[0].work_types) == ["cleaning", "loader"]


def test_normalize_admin_work_types():
    p = PostExtraction(
        is_casting=True,
        category="admin",
        vacancies=[
            VacancyExtraction(work_types=["supervisor", "registration_operator"]),
        ],
    )
    out = normalize_extracted(p)
    assert sorted(out.vacancies[0].work_types) == ["registration_operator", "supervisor"]


def test_normalize_drops_unknown_work_types():
    p = PostExtraction(
        is_casting=True,
        category="event",
        vacancies=[
            VacancyExtraction(work_types=["hostess", "garbage_code"]),
        ],
    )
    out = normalize_extracted(p)
    assert out.vacancies[0].work_types == ["hostess"]


def test_normalize_passes_post_category():
    p = PostExtraction(is_casting=True, category="event", confidence=0.9)
    out = normalize_extracted(p)
    assert out.category == "event"
```

- [ ] **Step 4: Запустить тесты**

```bash
pytest tests/test_normalize.py -v
```

Expected: все существующие тесты проходят, новые 5 тестов тоже проходят.

- [ ] **Step 5: Commit**

```bash
git add llm/base.py llm/normalize.py tests/test_normalize.py
git commit -m "$(cat <<'EOF'
feat(llm): per-category extraction in SYSTEM_PROMPT + normalize work_types

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Repository — проброс category и work_types в insert + ORM конвертер

**Files:**
- Modify: `D:\Documents\Claude\Projects\model_pro\db\repository.py`
- Modify: `D:\Documents\Claude\Projects\model_pro\db\matching.py` (`_orm_to_extractions`)

- [ ] **Step 1: В `insert_message_with_vacancies` пробросить новые поля**

Открыть `db/repository.py`. Найти `insert_message_with_vacancies` (около строки 183). В блоке `pg_insert(Message).values(...)` (~строка 200) добавить новое поле `category=extracted.category,` после `confidence=extracted.confidence,`:

```python
        msg_stmt = (
            pg_insert(Message)
            .values(
                tg_chat_id=tg_chat_id,
                tg_chat_username=tg_chat_username,
                tg_message_id=tg_message_id,
                text=text,
                text_hash=text_hash,
                is_casting=extracted.is_casting,
                project_types=list(extracted.project_types),
                city=extracted.city,
                summary=extracted.summary,
                confidence=extracted.confidence,
                category=extracted.category,
            )
            .on_conflict_do_nothing(index_elements=["tg_chat_id", "tg_message_id"])
            .returning(Message.id)
        )
```

В блоке `pg_insert(Vacancy).values(...)` (~строка 240) добавить два поля `category=v.category,` и `work_types=list(v.work_types),` после `role_label=v.role_label,`:

```python
                    vac_stmt = (
                        pg_insert(Vacancy)
                        .values(
                            message_id=message_id,
                            idx=idx,
                            role_types=list(v.role_types),
                            gender=v.gender,
                            age_min=v.age_min,
                            age_max=v.age_max,
                            rate=v.rate,
                            ethnicity=list(v.ethnicity),
                            height_min=v.height_min,
                            height_max=v.height_max,
                            body_type=list(v.body_type),
                            hair_color=list(v.hair_color),
                            hair_length=list(v.hair_length),
                            description=v.description,
                            role_label=v.role_label,
                            category=v.category,
                            work_types=list(v.work_types),
                        )
                        .returning(Vacancy.id)
                    )
```

- [ ] **Step 2: Расширить `_orm_to_extractions` в `db/matching.py`**

Открыть `db/matching.py`. Найти `_orm_to_extractions` (строка 136). Заменить целиком на:

```python
def _orm_to_extractions(
    message: Message,
    vacancies: list[Vacancy],
) -> tuple[PostExtraction, list[VacancyExtraction]]:
    """Конвертер ORM Message + Vacancy → Pydantic PostExtraction +
    VacancyExtraction.

    Используется в duplicate-пути userbot._handle_message: когда
    повторный прилёт того же текста обнаружен через find_canonical,
    мы поднимаем canonical из БД и прогоняем матчинг по его уже
    извлечённым вакансиям, не дёргая LLM повторно.

    Поля 1:1 совпадают между ORM и Pydantic — это просто перекладка.
    """
    post = PostExtraction(
        is_casting=message.is_casting,
        category=message.category,
        project_types=list(message.project_types),
        city=message.city,
        summary=message.summary,
        confidence=message.confidence,
        vacancies=[],
    )
    vac_extractions = [
        VacancyExtraction(
            role_types=list(v.role_types),
            work_types=list(v.work_types),
            category=v.category,
            gender=v.gender,
            age_min=v.age_min,
            age_max=v.age_max,
            rate=v.rate,
            ethnicity=list(v.ethnicity),
            height_min=v.height_min,
            height_max=v.height_max,
            body_type=list(v.body_type),
            hair_color=list(v.hair_color),
            hair_length=list(v.hair_length),
            description=v.description,
            role_label=v.role_label,
        )
        for v in vacancies
    ]
    return post, vac_extractions
```

- [ ] **Step 3: Запустить существующий тест конвертера**

```bash
pytest tests/test_matching_orm_convert.py -v
```

Existing tests должны пройти (новые поля добавляются как пустые в фикстурах). Если pydantic ругается на `Literal` в Vacancy.category, потому что фикстура не задаёт category — fixture либо передаёт `category=None`, либо тест проходит как есть (default=None в Pydantic).

Если какой-то тест падает с `TypeError: unexpected keyword argument 'category'` или подобным — это значит ORM Vacancy ещё не имеет поля. Проверить что Task 2 был выполнен.

- [ ] **Step 4: Smoke-test что repository функция импортируется**

```bash
python -c "from db.repository import insert_message_with_vacancies; print('ok')"
```

Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add db/repository.py db/matching.py
git commit -m "$(cat <<'EOF'
feat(db): pass category + work_types through insert + ORM converter

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Matcher refactor — dispatch + 4 per-category функции + tests (TDD)

**Files:**
- Modify: `D:\Documents\Claude\Projects\model_pro\db\matching.py` (полный рефактор)
- Create: `D:\Documents\Claude\Projects\model_pro\tests\test_matching_dispatch.py`
- Create: `D:\Documents\Claude\Projects\model_pro\tests\test_matching_event.py`
- Create: `D:\Documents\Claude\Projects\model_pro\tests\test_matching_general.py`
- Create: `D:\Documents\Claude\Projects\model_pro\tests\test_matching_admin.py`

- [ ] **Step 1: Написать failing-тесты для `_check_event_match` (TDD)**

Создать `tests/test_matching_event.py`:

```python
"""Юнит-тесты per-vacancy match для event-категории."""
from db.matching import _check_event_match
from db.models import EventProfile
from models.schemas import PostExtraction, VacancyExtraction


def _profile(**kw) -> EventProfile:
    p = EventProfile(
        user_id=1,
        full_name="Test",
        gender="female",
        city="Москва",
        ready_for_travel=False,
        actual_age=22,
        min_rate=3000,
        height_cm=170,
        body_type=["slim"],
        hair_color="brown",
        hair_length="long",
        ethnicity=["slavic"],
        work_types=["hostess", "promo_model"],
    )
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def _post(**kw) -> PostExtraction:
    base = dict(is_casting=True, category="event", city="Москва", confidence=0.9)
    base.update(kw)
    return PostExtraction(**base)


def _vacancy(**kw) -> VacancyExtraction:
    base = dict(work_types=["hostess"], gender="female", age_min=18, age_max=30)
    base.update(kw)
    return VacancyExtraction(**base)


def test_event_match_basic():
    assert _check_event_match(_profile(), _post(), _vacancy()) is True


def test_event_match_work_types_no_overlap():
    assert _check_event_match(_profile(work_types=["promo_model"]), _post(), _vacancy(work_types=["animator"])) is False


def test_event_match_work_types_empty_in_vacancy_means_no_filter():
    """Если в вакансии work_types пуст — фильтр не применяем."""
    assert _check_event_match(_profile(), _post(), _vacancy(work_types=[])) is True


def test_event_match_age_uses_actual_age_not_play_age():
    p = _profile(actual_age=35)
    v = _vacancy(age_min=18, age_max=25)
    assert _check_event_match(p, _post(), v) is False


def test_event_match_city_mismatch_blocks_unless_travel():
    p = _profile(city="СПб", ready_for_travel=False)
    assert _check_event_match(p, _post(city="Москва"), _vacancy()) is False
    p.ready_for_travel = True
    assert _check_event_match(p, _post(city="Москва"), _vacancy()) is True


def test_event_match_rate_below_min_blocks():
    p = _profile(min_rate=5000)
    v = _vacancy()
    v.rate = 3000
    assert _check_event_match(p, _post(), v) is False


def test_event_match_gender_mismatch_blocks():
    p = _profile(gender="female")
    v = _vacancy(gender="male")
    assert _check_event_match(p, _post(), v) is False


def test_event_match_height_out_of_range_blocks():
    p = _profile(height_cm=160)
    v = _vacancy(height_min=170, height_max=180)
    assert _check_event_match(p, _post(), v) is False


def test_event_match_body_type_no_overlap_blocks():
    p = _profile(body_type=["plus_size"])
    v = _vacancy(body_type=["athletic"])
    assert _check_event_match(p, _post(), v) is False


def test_event_match_optional_filters_when_vacancy_empty():
    """Если у вакансии не указаны body_type/hair_color/ethnicity/height — не фильтруем."""
    p = _profile(body_type=[], hair_color=None, ethnicity=[])
    v = _vacancy()  # без физ. требований
    assert _check_event_match(p, _post(), v) is True
```

- [ ] **Step 2: Написать failing-тесты для `_check_general_match`**

Создать `tests/test_matching_general.py`:

```python
"""Юнит-тесты per-vacancy match для general-категории."""
from db.matching import _check_general_match
from db.models import GeneralProfile
from models.schemas import PostExtraction, VacancyExtraction


def _profile(**kw) -> GeneralProfile:
    p = GeneralProfile(
        user_id=1,
        full_name="Test",
        gender="male",
        city="Москва",
        ready_for_travel=False,
        actual_age=30,
        min_rate=2000,
        work_types=["loader", "helper"],
    )
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def _post(**kw) -> PostExtraction:
    base = dict(is_casting=True, category="general", city="Москва", confidence=0.9)
    base.update(kw)
    return PostExtraction(**base)


def _vacancy(**kw) -> VacancyExtraction:
    base = dict(work_types=["loader"], age_min=18, age_max=50)
    base.update(kw)
    return VacancyExtraction(**base)


def test_general_match_basic():
    assert _check_general_match(_profile(), _post(), _vacancy()) is True


def test_general_match_work_types_no_overlap():
    assert _check_general_match(_profile(work_types=["cleaning"]), _post(), _vacancy(work_types=["loader"])) is False


def test_general_match_work_types_empty_in_vacancy():
    assert _check_general_match(_profile(), _post(), _vacancy(work_types=[])) is True


def test_general_match_age_uses_actual_age():
    assert _check_general_match(_profile(actual_age=60), _post(), _vacancy(age_min=18, age_max=50)) is False


def test_general_match_gender_mismatch_blocks():
    assert _check_general_match(_profile(gender="female"), _post(), _vacancy(gender="male")) is False


def test_general_match_rate_below_min_blocks():
    p = _profile(min_rate=5000)
    v = _vacancy()
    v.rate = 1500
    assert _check_general_match(p, _post(), v) is False


def test_general_match_does_not_filter_on_creative_fields():
    """ethnicity / body_type / hair / role_types / project_types — не используются."""
    v = _vacancy(ethnicity=["asian"], body_type=["athletic"], hair_color=["blond"])
    assert _check_general_match(_profile(), _post(), v) is True
```

- [ ] **Step 3: Написать failing-тесты для `_check_admin_match`**

Создать `tests/test_matching_admin.py`:

```python
"""Юнит-тесты per-vacancy match для admin-категории."""
from db.matching import _check_admin_match
from db.models import AdminProfile
from models.schemas import PostExtraction, VacancyExtraction


def _profile(**kw) -> AdminProfile:
    p = AdminProfile(
        user_id=1,
        full_name="Test",
        gender="female",
        city="Москва",
        ready_for_travel=False,
        actual_age=28,
        min_rate=2500,
        work_types=["registration_operator"],
    )
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def _post(**kw) -> PostExtraction:
    base = dict(is_casting=True, category="admin", city="Москва", confidence=0.9)
    base.update(kw)
    return PostExtraction(**base)


def _vacancy(**kw) -> VacancyExtraction:
    base = dict(work_types=["registration_operator"], age_min=20, age_max=40)
    base.update(kw)
    return VacancyExtraction(**base)


def test_admin_match_basic():
    assert _check_admin_match(_profile(), _post(), _vacancy()) is True


def test_admin_match_work_types_no_overlap():
    assert _check_admin_match(_profile(), _post(), _vacancy(work_types=["supervisor"])) is False


def test_admin_match_age_uses_actual_age():
    assert _check_admin_match(_profile(actual_age=50), _post(), _vacancy(age_min=20, age_max=40)) is False


def test_admin_match_does_not_filter_on_gender():
    """admin: gender не используется как гейт (часто не указывается в вакансии)."""
    p = _profile(gender="male")
    v = _vacancy(gender="female")
    assert _check_admin_match(p, _post(), v) is True


def test_admin_match_city_mismatch_blocks_unless_travel():
    p = _profile(city="СПб")
    assert _check_admin_match(p, _post(city="Москва"), _vacancy()) is False
    p.ready_for_travel = True
    assert _check_admin_match(p, _post(city="Москва"), _vacancy()) is True


def test_admin_match_rate_below_min_blocks():
    p = _profile(min_rate=5000)
    v = _vacancy()
    v.rate = 2000
    assert _check_admin_match(p, _post(), v) is False
```

- [ ] **Step 4: Написать тест диспатчера**

Создать `tests/test_matching_dispatch.py`:

```python
"""Юнит-тесты диспатчера: effective_cat = vacancy.category or post.category,
неизвестная категория → пропуск."""
from db.matching import _resolve_effective_category
from models.schemas import PostExtraction, VacancyExtraction


def test_resolve_uses_vacancy_category_when_set():
    post = PostExtraction(is_casting=True, category="event")
    v = VacancyExtraction(category="creative")
    assert _resolve_effective_category(post, v) == "creative"


def test_resolve_falls_back_to_post_category():
    post = PostExtraction(is_casting=True, category="event")
    v = VacancyExtraction(category=None)
    assert _resolve_effective_category(post, v) == "event"


def test_resolve_returns_none_when_both_none():
    post = PostExtraction(is_casting=True, category=None)
    v = VacancyExtraction(category=None)
    assert _resolve_effective_category(post, v) is None
```

- [ ] **Step 5: Запустить тесты — должны провалиться**

```bash
pytest tests/test_matching_event.py tests/test_matching_general.py tests/test_matching_admin.py tests/test_matching_dispatch.py -v
```

Expected: ImportError на `_check_event_match` / `_check_general_match` / `_check_admin_match` / `_resolve_effective_category` (функций ещё нет).

- [ ] **Step 6: Полностью переписать `db/matching.py`**

Заменить содержимое `D:\Documents\Claude\Projects\model_pro\db\matching.py` на:

```python
"""Сопоставление извлечённого объявления с анкетами пользователей.

Per-category архитектура: для каждой категории (creative/event/general/admin)
своя функция `_check_<cat>_match` с правилами + загрузка соответствующей
профиль-таблицы. Диспатчер `find_matching_vacancies` определяет
effective_cat по vacancy.category или post.category и вызывает нужный matcher.
"""
from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import select

from db.models import (
    AdminProfile,
    CreativeProfile,
    EventProfile,
    GeneralProfile,
    Message,
    UserCategorySubscription,
    Vacancy,
)
from db.session import AsyncSessionLocal
from models.schemas import PostExtraction, VacancyExtraction

# Минимальная уверенность LLM для рассылки. Ниже — игнорируем сообщение.
MIN_CONFIDENCE = 0.5


# ============================================================================
# Низкоуровневые помощники
# ============================================================================


def _ranges_overlap(a_lo: int, a_hi: int, b_lo: int, b_hi: int) -> bool:
    return not (a_hi < b_lo or a_lo > b_hi)


def _intersect(a: Iterable[str], b: Iterable[str]) -> bool:
    return bool(set(a) & set(b))


def _city_ok(post_city: Optional[str], profile_city: Optional[str], travel: bool) -> bool:
    """Город матчится либо когда совпадает, либо когда юзер готов к разъездам.
    Если в посте город не указан или у юзера нет — фильтр не применяется."""
    if not post_city or not profile_city:
        return True
    if post_city.lower() == profile_city.lower():
        return True
    return travel


def _gender_ok(vacancy_gender: Optional[str], profile_gender: Optional[str]) -> bool:
    """Если в вакансии указан конкретный пол — должен совпадать с профилем."""
    if not vacancy_gender:
        return True
    if not profile_gender:
        return True
    return vacancy_gender == profile_gender


def _rate_ok(vacancy_rate: Optional[int], profile_min_rate: Optional[int]) -> bool:
    """Ставка вакансии должна быть >= минимальной ставки юзера, если оба указаны."""
    if vacancy_rate is None or profile_min_rate is None:
        return True
    return vacancy_rate >= profile_min_rate


def _age_overlaps(
    vacancy_min: Optional[int],
    vacancy_max: Optional[int],
    profile_min: Optional[int],
    profile_max: Optional[int],
) -> bool:
    """Диапазон возраста вакансии пересекается с возрастом профиля.
    Если у вакансии нет возрастных требований — пропускаем."""
    if vacancy_min is None and vacancy_max is None:
        return True
    v_lo = vacancy_min if vacancy_min is not None else 0
    v_hi = vacancy_max if vacancy_max is not None else 120
    p_lo = profile_min if profile_min is not None else 0
    p_hi = profile_max if profile_max is not None else 120
    return _ranges_overlap(v_lo, v_hi, p_lo, p_hi)


def _height_ok(vacancy_min: Optional[int], vacancy_max: Optional[int], profile_height: Optional[int]) -> bool:
    if vacancy_min is None and vacancy_max is None:
        return True
    if profile_height is None:
        return True  # в профиле не указан — не фильтруем
    v_lo = vacancy_min if vacancy_min is not None else 0
    v_hi = vacancy_max if vacancy_max is not None else 999
    return v_lo <= profile_height <= v_hi


# ============================================================================
# Per-category matchers
# ============================================================================


def _check_creative_match(profile: CreativeProfile, post: PostExtraction, vacancy: VacancyExtraction) -> bool:
    """True, если creative-профиль подходит под вакансию.

    Использует play_age_min/max (играемый возраст). Учитывает project_types
    (post-level) и role_types (per-vacancy). Все физические параметры
    опциональны — фильтруются только если LLM их извлёк."""
    if not _gender_ok(vacancy.gender, profile.gender):
        return False
    if not _age_overlaps(vacancy.age_min, vacancy.age_max, profile.play_age_min, profile.play_age_max):
        return False
    if post.project_types and profile.project_types:
        if not _intersect(post.project_types, profile.project_types):
            return False
    if vacancy.role_types and profile.role_types:
        if not _intersect(vacancy.role_types, profile.role_types):
            return False
    if not _rate_ok(vacancy.rate, profile.min_rate):
        return False
    if vacancy.ethnicity and profile.ethnicity:
        if not _intersect(vacancy.ethnicity, profile.ethnicity):
            return False
    if not _height_ok(vacancy.height_min, vacancy.height_max, profile.height_cm):
        return False
    if vacancy.body_type and profile.body_type:
        if not _intersect(vacancy.body_type, profile.body_type):
            return False
    if vacancy.hair_color and profile.hair_color:
        if profile.hair_color not in vacancy.hair_color:
            return False
    if vacancy.hair_length and profile.hair_length:
        if profile.hair_length not in vacancy.hair_length:
            return False
    if not _city_ok(post.city, profile.city, profile.ready_for_travel):
        return False
    return True


def _check_event_match(profile: EventProfile, post: PostExtraction, vacancy: VacancyExtraction) -> bool:
    """True, если event-профиль подходит под вакансию.

    Использует actual_age (актуальный, single value). Обязательная проверка
    work_types (если в вакансии указаны). Физические параметры опциональны."""
    if vacancy.work_types and profile.work_types:
        if not _intersect(vacancy.work_types, profile.work_types):
            return False
    if not _gender_ok(vacancy.gender, profile.gender):
        return False
    if not _age_overlaps(vacancy.age_min, vacancy.age_max, profile.actual_age, profile.actual_age):
        return False
    if not _rate_ok(vacancy.rate, profile.min_rate):
        return False
    if vacancy.ethnicity and profile.ethnicity:
        if not _intersect(vacancy.ethnicity, profile.ethnicity):
            return False
    if not _height_ok(vacancy.height_min, vacancy.height_max, profile.height_cm):
        return False
    if vacancy.body_type and profile.body_type:
        if not _intersect(vacancy.body_type, profile.body_type):
            return False
    if vacancy.hair_color and profile.hair_color:
        if profile.hair_color not in vacancy.hair_color:
            return False
    if vacancy.hair_length and profile.hair_length:
        if profile.hair_length not in vacancy.hair_length:
            return False
    if not _city_ok(post.city, profile.city, profile.ready_for_travel):
        return False
    return True


def _check_general_match(profile: GeneralProfile, post: PostExtraction, vacancy: VacancyExtraction) -> bool:
    """True, если general-профиль подходит под вакансию.

    Только work_types + actual_age + gender + rate + city.
    physical_fitness НЕ матчится (поле осталось для UI/будущего)."""
    if vacancy.work_types and profile.work_types:
        if not _intersect(vacancy.work_types, profile.work_types):
            return False
    if not _gender_ok(vacancy.gender, profile.gender):
        return False
    if not _age_overlaps(vacancy.age_min, vacancy.age_max, profile.actual_age, profile.actual_age):
        return False
    if not _rate_ok(vacancy.rate, profile.min_rate):
        return False
    if not _city_ok(post.city, profile.city, profile.ready_for_travel):
        return False
    return True


def _check_admin_match(profile: AdminProfile, post: PostExtraction, vacancy: VacancyExtraction) -> bool:
    """True, если admin-профиль подходит под вакансию.

    Только work_types + actual_age + rate + city.
    gender и education НЕ матчятся (gender обычно не указывается, education
    оставлено в UI для будущего)."""
    if vacancy.work_types and profile.work_types:
        if not _intersect(vacancy.work_types, profile.work_types):
            return False
    if not _age_overlaps(vacancy.age_min, vacancy.age_max, profile.actual_age, profile.actual_age):
        return False
    if not _rate_ok(vacancy.rate, profile.min_rate):
        return False
    if not _city_ok(post.city, profile.city, profile.ready_for_travel):
        return False
    return True


# ============================================================================
# Диспатчер
# ============================================================================


def _resolve_effective_category(
    post: PostExtraction, vacancy: VacancyExtraction
) -> Optional[str]:
    """Resolve effective category: vacancy.category overrides post.category."""
    return vacancy.category or post.category


async def _load_profiles_for_category(category: str) -> list:
    """Загружает профили нужной таблицы с фильтром по UserCategorySubscription."""
    profile_classes = {
        "creative": CreativeProfile,
        "event": EventProfile,
        "general": GeneralProfile,
        "admin": AdminProfile,
    }
    Profile = profile_classes[category]
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Profile)
            .join(
                UserCategorySubscription,
                UserCategorySubscription.user_id == Profile.user_id,
            )
            .where(
                Profile.completed_at.is_not(None),
                UserCategorySubscription.category == category,
                UserCategorySubscription.enabled.is_(True),
            )
        )
        return list(res.scalars().all())


_CATEGORY_MATCHERS = {
    "creative": _check_creative_match,
    "event": _check_event_match,
    "general": _check_general_match,
    "admin": _check_admin_match,
}


async def find_matching_vacancies(
    post: PostExtraction,
    vacancies: list[VacancyExtraction],
) -> dict[int, list[int]]:
    """Возвращает {user_id: [индексы подошедших вакансий в списке `vacancies`]}.

    Гейтит по is_casting/confidence на уровне поста.
    Для каждой вакансии resolve effective_category (vacancy.category or
    post.category), загружает соответствующую профиль-таблицу и проверяет
    per-category matcher.
    """
    if not post.is_casting or post.confidence < MIN_CONFIDENCE or not vacancies:
        return {}

    # Кэш загруженных профилей по категории — чтобы не грузить дважды,
    # если в посте несколько вакансий одной категории.
    profiles_cache: dict[str, list] = {}
    out: dict[int, list[int]] = {}

    for idx, v in enumerate(vacancies):
        eff_cat = _resolve_effective_category(post, v)
        if eff_cat is None:
            continue
        matcher = _CATEGORY_MATCHERS.get(eff_cat)
        if matcher is None:
            continue
        if eff_cat not in profiles_cache:
            profiles_cache[eff_cat] = await _load_profiles_for_category(eff_cat)
        for profile in profiles_cache[eff_cat]:
            if matcher(profile, post, v):
                out.setdefault(profile.user_id, []).append(idx)
    return out


# ============================================================================
# ORM → Pydantic конвертер (используется в duplicate-пути userbot._handle_message)
# ============================================================================


def _orm_to_extractions(
    message: Message,
    vacancies: list[Vacancy],
) -> tuple[PostExtraction, list[VacancyExtraction]]:
    """Конвертер ORM Message + Vacancy → Pydantic PostExtraction +
    VacancyExtraction.

    Поля 1:1 совпадают между ORM и Pydantic — это просто перекладка.
    """
    post = PostExtraction(
        is_casting=message.is_casting,
        category=message.category,
        project_types=list(message.project_types),
        city=message.city,
        summary=message.summary,
        confidence=message.confidence,
        vacancies=[],
    )
    vac_extractions = [
        VacancyExtraction(
            role_types=list(v.role_types),
            work_types=list(v.work_types),
            category=v.category,
            gender=v.gender,
            age_min=v.age_min,
            age_max=v.age_max,
            rate=v.rate,
            ethnicity=list(v.ethnicity),
            height_min=v.height_min,
            height_max=v.height_max,
            body_type=list(v.body_type),
            hair_color=list(v.hair_color),
            hair_length=list(v.hair_length),
            description=v.description,
            role_label=v.role_label,
        )
        for v in vacancies
    ]
    return post, vac_extractions
```

(Старая `matches()` функция удалена — её замена `_check_creative_match`. Никто извне `matches()` не вызывает в этом коде, проверено grep'ом.)

- [ ] **Step 7: Запустить новые тесты — должны пройти**

```bash
pytest tests/test_matching_event.py tests/test_matching_general.py tests/test_matching_admin.py tests/test_matching_dispatch.py -v
```

Expected: все тесты проходят.

- [ ] **Step 8: Запустить весь существующий testsuite — ничего не сломали**

```bash
pytest tests/ -v 2>&1 | tail -20
```

Expected: 80+ tests pass, ничего не сломано.

Если падают тесты — это могут быть `tests/test_matching_orm_convert.py` или `tests/test_normalize.py`, проверить совместимость с новыми полями.

Если падает старый тест с импортом `from db.matching import matches` — найти и заменить на `_check_creative_match`. Поиск: `grep -rn "from db.matching import" tests/`. Если такие тесты есть — переписать через новый API.

- [ ] **Step 9: Smoke-test repository интеграции**

```bash
python -c "from db.matching import find_matching_vacancies, _resolve_effective_category, _check_event_match, _check_general_match, _check_admin_match, _check_creative_match; print('all matchers ok')"
```

Expected: `all matchers ok`.

- [ ] **Step 10: Commit**

```bash
git add db/matching.py tests/test_matching_event.py tests/test_matching_general.py tests/test_matching_admin.py tests/test_matching_dispatch.py
git commit -m "$(cat <<'EOF'
feat(matching): per-category dispatch — _check_<cat>_match × 4 + tests

- _check_creative_match (renamed from matches, same logic).
- _check_event_match: work_types + actual_age + physical params (opt).
- _check_general_match: work_types + actual_age + city + rate.
- _check_admin_match: work_types + actual_age + city + rate.
- _resolve_effective_category: vacancy.category or post.category.
- find_matching_vacancies dispatches via _CATEGORY_MATCHERS dict;
  loads only relevant *Profile table per resolved category.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Push branch + open PR

- [ ] **Step 1: Push branch**

```bash
git push -u origin feat/per-category-matching
```

- [ ] **Step 2: Create PR**

```bash
gh pr create --title "feat: per-category matching for event/general/admin" --body "$(cat <<'EOF'
## Summary

Юзеры с подписками на event / general / admin теперь получают релевантные уведомления (раньше работала только creative).

### Что меняется
- **LLM-extract**: PostExtraction.category + VacancyExtraction.{category, work_types}. SYSTEM_PROMPT расширен описаниями 4 категорий и whitelist'ами work_types.
- **БД**: миграция 0016 добавляет messages.category, vacancies.{category, work_types}. Бэкфилл существующих casting-постов: category='creative'.
- **Reference data**: WORK_TYPES_EVENT/GENERAL/ADMIN. Pydantic-валидаторы на этих справочниках.
- **Matcher**: dispatch-таблица 4 функций _check_<cat>_match. Каждая загружает свою *Profile с фильтром по UserCategorySubscription. Возраст для creative по play_age, для остальных — actual_age.
- **Cutover**: старая matches() удалена, заменена на _check_creative_match с той же логикой.

### Test plan
- [x] `pytest tests/` — 80+ тестов, новые: 5 normalize, 9 event, 7 general, 6 admin, 3 dispatch
- [ ] После деплоя: проверить логи userbot — extract.category для event/general/admin постов
- [ ] Проверить новые юзеры event категории получают уведомления на релевантных постах
- [ ] SQL-чек: `SELECT category, COUNT(*) FROM messages WHERE is_casting=TRUE GROUP BY category` — должны появиться event/general/admin

## Spec
docs/superpowers/specs/2026-05-08-per-category-matching-design.md

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: Сообщить URL PR**

После успешного `gh pr create` — записать URL в отчёт.

---

## Self-review notes

**Spec coverage:**
- Расширение Pydantic — Task 1 ✓
- Миграция 0016 + ORM — Task 2 ✓
- LLM SYSTEM_PROMPT + normalize — Task 3 ✓
- Repository проброс полей + ORM-конвертер — Task 4 ✓
- Matcher dispatch + 4 _check_<cat>_match + tests — Task 5 ✓
- Cutover (старая matches удаляется) — Task 5 Step 6 ✓
- Reference data work_types_event/general/admin — Task 1 Step 2 ✓
- Бэкфилл messages.category='creative' для is_casting=true — Task 2 Step 1 (в миграции) ✓

**Известные нюансы:**
- Task 2 содержит ветку «если в Message уже есть legacy `category` — переименовать в `legacy_category`». Имплементер должен проверить `db/models.py` и решить.
- Task 3 нормализует work_types через объединение трёх whitelist'ов (event + general + admin), потому что на этапе normalize мы ещё не знаем категорию вакансии надёжно. Per-category whitelist применяется неявно: например, vacancy.work_types=["loader"] для event-вакансии останется в коде, но per-category matcher проверит что у профиля event есть пересечение work_types — а у event-юзера loader быть не может (валидация в EventProfileSchema), так что в практике невалидное пройдёт без вреда.
- Task 5 удаляет старую функцию `matches()`. Если где-то в проекте есть legacy импорты `from db.matching import matches` — их заменить.
