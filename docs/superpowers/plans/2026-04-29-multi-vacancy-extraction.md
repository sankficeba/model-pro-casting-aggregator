# Multi-Vacancy Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Заменить один-к-одному «пост = строка в `messages`» на два уровня (пост + N вакансий), чтобы посты с несколькими ролями (разные гонорары / возрасты / типы ролей) хранились корректно, матчились пер-вакансия и приходили одной агрегированной карточкой с нужными ролями.

**Architecture:** Новая таблица `vacancies` (FK → `messages`, CASCADE) хранит per-role поля: `role_types, gender, age_min/max, rate, description, role_label, idx`. `messages` — post-level: `project_types, city, summary, is_casting, confidence`. LLM возвращает `PostExtraction` с вложенным `vacancies[]`. Матчинг итерируется по вакансиям; одно агрегированное уведомление на пост (дедуп `(user_id, message_id)`, в `notifications.matched_vacancy_ids` пишутся id попавших вакансий). Миграция бэкфилит 1 вакансию на каждый исторический `is_casting=true`.

**Tech Stack:** Python 3, SQLAlchemy 2 async, Alembic, Pydantic 2, FastAPI, Telethon, aiogram, loguru, pytest, pytest-asyncio. Frontend: React/TS/Tailwind (webapp).

**Spec:** `docs/superpowers/specs/2026-04-29-multi-vacancy-extraction-design.md`

---

## Notes for the executor

- **Тестов в проекте сейчас нет.** Их инфраструктуру поднимаем в Task 1. Все тесты — pure-Python unit-уровня (без Postgres), DB-логика проверяется руками в Task 13.
- **Russian commit messages** — текущая история уже на смеси ru/en, держимся короткого conventional-style на английском (`feat:`, `refactor:`, `test:`, `chore:`).
- **Запуск pytest:** локально из корня проекта `pytest tests/ -v`. Если venv не активирован — `python -m pytest tests/ -v`.
- **Не трогать legacy-колонки** `messages.gender / age_min / age_max / role_types / rate / age / category` — оставляем на месте, только перестаём писать/читать.

---

### Task 1: Поднять pytest

**Files:**
- Create: `requirements-dev.txt`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `pytest.ini`

- [ ] **Step 1: Создать `requirements-dev.txt`**

```
-r requirements.txt
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 2: Создать `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

- [ ] **Step 3: Создать `tests/__init__.py`** (пустой)

- [ ] **Step 4: Создать `tests/conftest.py`**

```python
"""Общие фикстуры. БД тут НЕ инициализируем — все тесты в этом наборе
работают на чистой логике (schemas, normalize, matching, format)."""
```

- [ ] **Step 5: Установить зависимости и проверить, что pytest стартует**

Run: `pip install -r requirements-dev.txt && pytest tests/ -v`
Expected: `no tests ran` (без ошибок)

- [ ] **Step 6: Commit**

```bash
git add requirements-dev.txt pytest.ini tests/__init__.py tests/conftest.py
git commit -m "chore: bootstrap pytest test infrastructure"
```

---

### Task 2: Pydantic-схемы `PostExtraction` / `VacancyExtraction`

**Files:**
- Modify: `models/schemas.py` (заменяем `ExtractedData`)
- Test: `tests/test_schemas.py`

- [ ] **Step 1: Написать падающий тест**

`tests/test_schemas.py`:

```python
"""Контракт PostExtraction / VacancyExtraction."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from models.schemas import PostExtraction, VacancyExtraction


def test_vacancy_minimal_defaults():
    v = VacancyExtraction()
    assert v.role_types == []
    assert v.gender is None
    assert v.age_min is None
    assert v.age_max is None
    assert v.rate is None
    assert v.description is None
    assert v.role_label is None


def test_post_minimal_defaults():
    p = PostExtraction()
    assert p.is_casting is False
    assert p.project_types == []
    assert p.city is None
    assert p.summary is None
    assert p.confidence == 0.0
    assert p.vacancies == []


def test_post_with_vacancies():
    p = PostExtraction(
        is_casting=True,
        project_types=["kino_serial"],
        city="Москва",
        summary="Сериал XYZ — 2 роли",
        confidence=0.9,
        vacancies=[
            VacancyExtraction(
                role_types=["main"], gender="female",
                age_min=35, age_max=45, rate=8000,
                description="Мама — 35–45, ставка 8000₽",
                role_label="Мама",
            ),
            VacancyExtraction(
                role_types=["episode"], gender="male",
                age_min=8, age_max=10, rate=5000,
                description="Сын — 8–10 лет",
                role_label="Сын",
            ),
        ],
    )
    assert len(p.vacancies) == 2
    assert p.vacancies[0].role_label == "Мама"
    assert p.vacancies[1].age_min == 8


def test_age_validation_bounds():
    with pytest.raises(ValidationError):
        VacancyExtraction(age_min=-1)
    with pytest.raises(ValidationError):
        VacancyExtraction(age_max=200)


def test_confidence_bounds():
    with pytest.raises(ValidationError):
        PostExtraction(confidence=1.5)
    with pytest.raises(ValidationError):
        PostExtraction(confidence=-0.1)


def test_extracted_data_no_longer_exists():
    """Убедимся, что старая модель удалена — никто не должен на неё ссылаться."""
    import models.schemas as m
    assert not hasattr(m, "ExtractedData")
```

- [ ] **Step 2: Запустить — должно упасть на импорте**

Run: `pytest tests/test_schemas.py -v`
Expected: ImportError / ModuleNotFoundError на `PostExtraction`

- [ ] **Step 3: Заменить содержимое `models/schemas.py`**

```python
"""Pydantic-схемы для извлечённых данных и пользовательских фильтров."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class VacancyExtraction(BaseModel):
    """Одна вакансия (роль) внутри поста."""

    role_types: list[str] = []
    gender: Optional[Literal["male", "female"]] = None
    age_min: Optional[int] = Field(None, ge=0, le=120)
    age_max: Optional[int] = Field(None, ge=0, le=120)
    rate: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    role_label: Optional[str] = None


class PostExtraction(BaseModel):
    """Структура, которую LLM извлекает из объявления о кастинге.

    Поля поста (project_types, city, summary, is_casting, confidence) —
    общие для всего объявления; vacancies — список ролей, у каждой свои
    условия (gender / age / rate / role_types).
    """

    is_casting: bool = False
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

- [ ] **Step 4: Запустить тесты**

Run: `pytest tests/test_schemas.py -v`
Expected: все 6 тестов PASS

- [ ] **Step 5: Commit**

```bash
git add models/schemas.py tests/test_schemas.py
git commit -m "refactor: split ExtractedData into PostExtraction + VacancyExtraction"
```

---

### Task 3: Нормализация per-vacancy в `normalize.py`

**Files:**
- Modify: `llm/normalize.py`
- Test: `tests/test_normalize.py`

- [ ] **Step 1: Написать падающий тест**

`tests/test_normalize.py`:

```python
"""normalize_extracted: канонизация project_types/role_types на обоих уровнях."""
from __future__ import annotations

from models.schemas import PostExtraction, VacancyExtraction
from llm.normalize import normalize_extracted


def test_normalizes_post_project_types():
    p = PostExtraction(
        is_casting=True,
        project_types=["реклама", "kino_serial"],  # label + code
    )
    out = normalize_extracted(p)
    assert "advertising" in out.project_types
    assert "kino_serial" in out.project_types


def test_normalizes_per_vacancy_role_types():
    p = PostExtraction(
        is_casting=True,
        vacancies=[
            VacancyExtraction(role_types=["главная роль"]),  # label
            VacancyExtraction(role_types=["episode", "trash-неизвестный"]),
        ],
    )
    out = normalize_extracted(p)
    assert out.vacancies[0].role_types == ["main"]
    assert out.vacancies[1].role_types == ["episode"]  # неизвестный код выкинули


def test_preserves_non_normalized_fields():
    p = PostExtraction(
        is_casting=True,
        city="Москва",
        confidence=0.7,
        vacancies=[
            VacancyExtraction(
                gender="female", age_min=20, age_max=30, rate=5000,
                description="d", role_label="Маша",
            ),
        ],
    )
    out = normalize_extracted(p)
    assert out.city == "Москва"
    assert out.confidence == 0.7
    v = out.vacancies[0]
    assert v.gender == "female"
    assert v.age_min == 20
    assert v.rate == 5000
    assert v.role_label == "Маша"
```

- [ ] **Step 2: Запустить — должно упасть** (импорт `PostExtraction`/`VacancyExtraction` в normalize ещё не настроен)

Run: `pytest tests/test_normalize.py -v`
Expected: ImportError или AttributeError

- [ ] **Step 3: Переписать `llm/normalize.py`**

```python
"""Постобработка LLM-extract: подменяем русские лейблы и опечатки на
канонические коды из api/reference_data.py.

Зачем: gpt-4o-mini периодически возвращает в project_types/role_types
лейбл вместо кода ("реклама" вместо "advertising"). Из-за этого сравнение
set'ов в db.matching ничего не находит, и пользователь не получает
уведомление. Нормализуем, чтобы матчинг работал даже при таких ошибках.
"""
from __future__ import annotations

from api.reference_data import all_refs
from models.schemas import PostExtraction, VacancyExtraction


def _build_indexes() -> tuple[dict[str, set[str]], dict[str, dict[str, str]]]:
    refs = all_refs()
    codes_by: dict[str, set[str]] = {}
    label_to_code_by: dict[str, dict[str, str]] = {}
    for category, items in refs.items():
        codes_by[category] = {it["code"] for it in items}
        label_to_code_by[category] = {it["label"].lower(): it["code"] for it in items}
    return codes_by, label_to_code_by


_CODES, _LABELS = _build_indexes()


def _normalize_one(category: str, raw: str) -> str | None:
    valid = _CODES.get(category, set())
    label_map = _LABELS.get(category, {})
    s = (raw or "").strip()
    if not s:
        return None
    if s in valid:
        return s
    code = label_map.get(s.lower())
    if code:
        return code
    cleaned = s.lower().replace("-", " ").replace("_", " ").strip()
    return label_map.get(cleaned)


def _normalize_list(category: str, raw: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for x in raw or []:
        norm = _normalize_one(category, x)
        if norm is not None and norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


def _normalize_vacancy(v: VacancyExtraction) -> VacancyExtraction:
    return v.model_copy(
        update={"role_types": _normalize_list("role_types", v.role_types)}
    )


def normalize_extracted(data: PostExtraction) -> PostExtraction:
    """Возвращает копию PostExtraction с нормализованными списками кодов
    на уровне поста (project_types) и каждой вакансии (role_types)."""
    return data.model_copy(
        update={
            "project_types": _normalize_list("project_types", data.project_types),
            "vacancies": [_normalize_vacancy(v) for v in data.vacancies],
        }
    )
```

- [ ] **Step 4: Запустить тесты**

Run: `pytest tests/test_normalize.py -v`
Expected: все 3 PASS

- [ ] **Step 5: Commit**

```bash
git add llm/normalize.py tests/test_normalize.py
git commit -m "refactor: normalize role_types per vacancy"
```

---

### Task 4: LLM `SYSTEM_PROMPT` и `extract()` под новую схему

**Files:**
- Modify: `llm/base.py`
- Test: `tests/test_llm_base.py`

- [ ] **Step 1: Написать тест на extract() с фейковым провайдером**

`tests/test_llm_base.py`:

```python
"""LLMProvider.extract: парсинг JSON под PostExtraction + нормализация."""
from __future__ import annotations

import json

from llm.base import LLMProvider
from models.schemas import PostExtraction


class _FakeProvider(LLMProvider):
    def __init__(self, raw: str) -> None:
        self._raw = raw

    async def _complete_json(self, system: str, user: str) -> str:  # noqa: ARG002
        return self._raw


async def test_extract_multi_vacancy():
    raw = json.dumps({
        "is_casting": True,
        "project_types": ["реклама"],
        "city": "Москва",
        "summary": "Реклама бренда X",
        "confidence": 0.85,
        "vacancies": [
            {"role_types": ["main"], "gender": "female",
             "age_min": 25, "age_max": 35, "rate": 12000,
             "description": "Героиня — девушка 25–35", "role_label": "Героиня"},
            {"role_types": ["episode"], "gender": "male",
             "age_min": 30, "age_max": 40, "rate": 8000,
             "description": "Партнёр — мужчина 30–40", "role_label": "Партнёр"},
        ],
    })
    out = await _FakeProvider(raw).extract("ignored")
    assert isinstance(out, PostExtraction)
    assert out.is_casting is True
    assert out.project_types == ["advertising"]  # нормализовано
    assert len(out.vacancies) == 2
    assert out.vacancies[0].role_label == "Героиня"


async def test_extract_no_vacancies_forces_not_casting():
    """Если LLM сказал is_casting=true, но vacancies пусто — форсим false."""
    raw = json.dumps({"is_casting": True, "confidence": 0.9, "vacancies": []})
    out = await _FakeProvider(raw).extract("ignored")
    assert out.is_casting is False


async def test_extract_invalid_json_returns_zero_confidence():
    out = await _FakeProvider("not a json").extract("ignored")
    assert out.confidence == 0.0
    assert out.is_casting is False
    assert out.vacancies == []


async def test_extract_strips_markdown_wrapper():
    raw = "```json\n" + json.dumps({"is_casting": False, "vacancies": []}) + "\n```"
    out = await _FakeProvider(raw).extract("ignored")
    assert out.is_casting is False
```

- [ ] **Step 2: Запустить — должно упасть**

Run: `pytest tests/test_llm_base.py -v`
Expected: FAIL (старый ExtractedData импортируется в base.py)

- [ ] **Step 3: Переписать `llm/base.py`**

```python
"""Абстрактный интерфейс LLM-провайдера."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger
from pydantic import ValidationError

from llm.normalize import normalize_extracted
from models.schemas import PostExtraction

SYSTEM_PROMPT = """Ты разбираешь объявления о кастингах на актёров и моделей
из Telegram-каналов. Из присланного сообщения нужно извлечь параметры
поиска и вернуть СТРОГО JSON-объект без markdown-обёрток.

Структура поста:
{
  "is_casting": bool,                    // это объявление о кастинге?
                                         // false для рекламы услуг, обучения и т.п.
  "project_types": [str],                // подмножество кодов:
                                         // kino_serial, advertising, model_projects,
                                         // show_reality, voice_dub, theater
  "city": str|null,                      // город съёмки на русском
  "summary": str|null,                   // краткое описание поста до 30 слов
  "confidence": float,                   // 0.0-1.0, твоя уверенность
  "vacancies": [                         // список ролей; пустой если is_casting=false
    {
      "role_types": [str],               // подмножество кодов:
                                         // main, supporting, episode, massovka,
                                         // groupovka, dubler, kaskader, model,
                                         // photo_model, promo_model, tv_host, diktor,
                                         // dancer, ballerina, gymnast, vocalist, musician
      "gender": "male"|"female"|null,    // кого ищут на эту роль
      "age_min": int|null,               // нижний возраст; для одного значения 25 — age_min=age_max=25
      "age_max": int|null,
      "rate": int|null,                  // ставка в рублях за смену; диапазон — нижняя граница
      "description": str|null,           // фрагмент поста об этой роли
      "role_label": str|null             // короткое имя роли как в посте: "Мама", "Сын", "Прохожий"
    }
  ]
}

ВАЖНО:
- Если в посте описана одна роль — vacancies массив длины 1.
- Если описаны несколько разных ролей с разными условиями (возрастом,
  гонораром, полом) — заводи на каждую отдельную запись в vacancies.
- Если is_casting=false — vacancies должно быть пустым массивом.
- Никаких комментариев, только JSON.
"""


def _try_parse_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"Не найден JSON в ответе LLM: {raw!r}")
    return json.loads(raw[start : end + 1])


class LLMProvider(ABC):
    @abstractmethod
    async def _complete_json(self, system: str, user: str) -> str:
        """Возвращает «сырой» ответ модели (ожидается JSON-строка)."""

    async def extract(self, text: str) -> PostExtraction:
        try:
            raw = await self._complete_json(SYSTEM_PROMPT, text)
        except Exception as e:  # noqa: BLE001
            logger.exception("LLM call failed: {}", e)
            return PostExtraction(confidence=0.0)

        try:
            data = _try_parse_json(raw)
            parsed = PostExtraction(**data)
        except (ValueError, ValidationError, json.JSONDecodeError) as e:
            logger.warning("Не удалось распарсить ответ LLM: {} | raw={!r}", e, raw)
            return PostExtraction(confidence=0.0)

        # Согласованность: is_casting=true без вакансий — бессмысленно.
        if parsed.is_casting and not parsed.vacancies:
            logger.warning(
                "LLM вернул is_casting=true с пустым vacancies — форсим is_casting=false"
            )
            parsed = parsed.model_copy(update={"is_casting": False})

        normalized = normalize_extracted(parsed)
        if normalized.project_types != parsed.project_types:
            logger.debug(
                "Нормализация project_types: {} -> {}",
                parsed.project_types, normalized.project_types,
            )
        return normalized
```

- [ ] **Step 4: Запустить тесты**

Run: `pytest tests/test_llm_base.py -v`
Expected: все 4 PASS

- [ ] **Step 5: Commit**

```bash
git add llm/base.py tests/test_llm_base.py
git commit -m "feat: LLM extract returns PostExtraction with vacancies[]"
```

---

### Task 5: Адаптировать `StubProvider`

**Files:**
- Modify: `llm/stub_provider.py`
- Test: `tests/test_stub_provider.py`

- [ ] **Step 1: Написать тест**

`tests/test_stub_provider.py`:

```python
from llm.stub_provider import StubProvider


async def test_stub_casting_one_vacancy():
    text = "Кастинг на сериал. Ищем девушку 25-30 лет."
    out = await StubProvider().extract(text)
    assert out.is_casting is True
    assert len(out.vacancies) == 1
    v = out.vacancies[0]
    assert v.gender == "female"
    assert v.age_min == 25
    assert v.age_max == 30


async def test_stub_non_casting_empty_vacancies():
    out = await StubProvider().extract("Продаю гараж недорого")
    assert out.is_casting is False
    assert out.vacancies == []
```

- [ ] **Step 2: Запустить — упадёт на импорте `ExtractedData`**

Run: `pytest tests/test_stub_provider.py -v`

- [ ] **Step 3: Переписать `llm/stub_provider.py`**

```python
"""Заглушка LLM: без внешних API, грубое извлечение по ключевым словам.
Эмулирует один-вакансия-на-пост (мульти-вакансия для regex-стаба нереалистична).
"""
from __future__ import annotations

import re

from loguru import logger

from llm.base import LLMProvider
from models.schemas import PostExtraction, VacancyExtraction

_MALE_WORDS = {
    "мужчина", "мужчины", "парень", "парни", "юноша", "мужской",
    "male", "man", "boy",
}
_FEMALE_WORDS = {
    "женщина", "девушка", "девочка", "женский", "дама",
    "female", "woman", "girl",
}
_CASTING_HINTS = (
    "кастинг", "съёмк", "съемк", "роль", "актёр", "актер", "актрис",
    "модел", "проект", "клип", "сериал", "реклам",
)


def _detect_gender(text: str) -> str | None:
    words = set(re.findall(r"\b\w+\b", text.lower()))
    if words & _MALE_WORDS:
        return "male"
    if words & _FEMALE_WORDS:
        return "female"
    return None


def _detect_age_range(text: str) -> tuple[int | None, int | None]:
    m = re.search(r"(\d{1,2})\s*[-–—]\s*(\d{1,2})", text)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        if 5 <= lo <= 100 and 5 <= hi <= 100 and lo <= hi:
            return lo, hi
    m = re.search(r"от\s+(\d{1,2})\s+до\s+(\d{1,2})", text, re.IGNORECASE)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"\b(\d{1,2})\s*(?:лет|года|год)\b", text, re.IGNORECASE)
    if m:
        age = int(m.group(1))
        if 5 <= age <= 100:
            return age, age
    return None, None


class StubProvider(LLMProvider):
    """Эмулирует LLM regex-эвристиками. Никаких внешних запросов."""

    async def _complete_json(self, system: str, user: str) -> str:  # noqa: ARG002
        return "{}"

    async def extract(self, text: str) -> PostExtraction:
        low = text.lower()
        is_casting = any(h in low for h in _CASTING_HINTS)
        gender = _detect_gender(text)
        age_min, age_max = _detect_age_range(text)
        summary = text.strip().replace("\n", " ")[:160]

        hits = sum(x is not None for x in (gender, age_min)) + (1 if is_casting else 0)
        confidence = min(1.0, 0.4 + 0.15 * hits)

        vacancies: list[VacancyExtraction] = []
        if is_casting:
            vacancies = [
                VacancyExtraction(
                    gender=gender,  # type: ignore[arg-type]
                    age_min=age_min,
                    age_max=age_max,
                    description=summary or None,
                ),
            ]

        result = PostExtraction(
            is_casting=is_casting,
            summary=summary or None,
            confidence=confidence,
            vacancies=vacancies,
        )
        logger.debug("StubProvider extracted: {}", result.model_dump())
        return result
```

- [ ] **Step 4: Запустить тесты**

Run: `pytest tests/test_stub_provider.py -v`
Expected: оба PASS

- [ ] **Step 5: Commit**

```bash
git add llm/stub_provider.py tests/test_stub_provider.py
git commit -m "refactor: StubProvider returns PostExtraction with single-vacancy"
```

---

### Task 6: SQLAlchemy-модель `Vacancy` + связь + `notifications.matched_vacancy_ids`

**Files:**
- Modify: `db/models.py`

Один технический шаг — модели не покрываем юнит-тестами (там нечего тестировать без живой БД, проверим в Task 13).

- [ ] **Step 1: Открыть `db/models.py` и добавить `Vacancy`** (вставить ПОСЛЕ класса `Message`, перед `Notification`)

```python
class Vacancy(Base):
    """Одна вакансия (роль) внутри объявления о кастинге.
    Один Message → 0..N Vacancy."""

    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Порядок вакансии в посте (0,1,2...): даёт стабильный UX и
    # защищает от дубля при ретрае LLM-extract'а.
    idx: Mapped[int] = mapped_column(Integer, nullable=False)
    role_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False,
    )
    gender: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    age_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    age_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role_label: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    message: Mapped["Message"] = relationship(back_populates="vacancies")

    __table_args__ = (
        UniqueConstraint("message_id", "idx", name="uq_vacancies_message_idx"),
    )
```

- [ ] **Step 2: Добавить обратную связь в класс `Message`**

В `db/models.py:181` (класс `Message`), после блока с историческими полями (`age`, `category`) добавить:

```python
    vacancies: Mapped[list["Vacancy"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="Vacancy.idx",
    )
```

- [ ] **Step 3: Добавить `matched_vacancy_ids` в `Notification`**

В классе `Notification` (после `error`):

```python
    matched_vacancy_ids: Mapped[Optional[list[int]]] = mapped_column(
        ARRAY(Integer), nullable=True,
    )
```

- [ ] **Step 4: Sanity-check импортов**

Run: `python -c "from db.models import Vacancy, Message, Notification; print('OK')"`
Expected: `OK` (без ImportError; миграцию ещё не накатили — но это импорт-проверка чисто на синтаксис/типы)

- [ ] **Step 5: Commit**

```bash
git add db/models.py
git commit -m "feat: add Vacancy ORM model + Message.vacancies relationship"
```

---

### Task 7: Alembic-миграция `0007_vacancies` (create + alter + backfill)

**Files:**
- Create: `migrations/versions/0007_vacancies.py`

- [ ] **Step 1: Создать файл миграции**

```python
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
```

- [ ] **Step 2: Проверить, что alembic видит ревизию**

Run: `alembic history --verbose | head -20`
Expected: видна ревизия `0007_vacancies (head)`, родитель `0006_messages_casting`.

- [ ] **Step 3: Commit** (саму миграцию накатим в Task 13 на чистой тестовой БД)

```bash
git add migrations/versions/0007_vacancies.py
git commit -m "feat(migration): add vacancies table + backfill from messages"
```

---

### Task 8: `repository.insert_message_with_vacancies` + `log_notification(matched_vacancy_ids=)`

**Files:**
- Modify: `db/repository.py`

- [ ] **Step 1: Открыть `db/repository.py`** и **заменить `insert_message`** (строки `db/repository.py:105-154`) на:

```python
async def insert_message_with_vacancies(
    *,
    tg_chat_id: int,
    tg_chat_username: str | None,
    tg_message_id: int,
    text: str,
    extracted: PostExtraction,
) -> tuple[Optional[int], list[int]]:
    """Вставить пост и его вакансии одной транзакцией.

    Возвращает (message_id, [vacancy_id, ...]).
    Если такое сообщение уже было (chat_id, msg_id) — возвращает
    существующий message_id и существующие vacancy_id (без пересоздания).
    """
    async with AsyncSessionLocal() as session:
        msg_stmt = (
            pg_insert(Message)
            .values(
                tg_chat_id=tg_chat_id,
                tg_chat_username=tg_chat_username,
                tg_message_id=tg_message_id,
                text=text,
                is_casting=extracted.is_casting,
                project_types=list(extracted.project_types),
                city=extracted.city,
                summary=extracted.summary,
                confidence=extracted.confidence,
            )
            .on_conflict_do_nothing(index_elements=["tg_chat_id", "tg_message_id"])
            .returning(Message.id)
        )
        try:
            res = await session.execute(msg_stmt)
            message_id = res.scalar_one_or_none()
            freshly_inserted = message_id is not None

            if message_id is None:
                # Дубль — достаём существующий
                existing = await session.execute(
                    select(Message.id).where(
                        Message.tg_chat_id == tg_chat_id,
                        Message.tg_message_id == tg_message_id,
                    )
                )
                message_id = existing.scalar_one_or_none()
                if message_id is None:
                    await session.rollback()
                    return None, []

            vacancy_ids: list[int] = []

            if freshly_inserted and extracted.is_casting and extracted.vacancies:
                for idx, v in enumerate(extracted.vacancies):
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
                            description=v.description,
                            role_label=v.role_label,
                        )
                        .returning(Vacancy.id)
                    )
                    vac_res = await session.execute(vac_stmt)
                    vacancy_ids.append(vac_res.scalar_one())
            else:
                # Дубль или non-casting: подхватываем существующие вакансии
                vac_existing = await session.execute(
                    select(Vacancy.id)
                    .where(Vacancy.message_id == message_id)
                    .order_by(Vacancy.idx)
                )
                vacancy_ids = [v for v in vac_existing.scalars().all()]

            await session.commit()
            return message_id, vacancy_ids
        except Exception as e:  # noqa: BLE001
            logger.exception("insert_message_with_vacancies failed: {}", e)
            await session.rollback()
            return None, []
```

- [ ] **Step 2: Заменить импорт и `log_notification`**

В `db/repository.py:12-14` обновить импорты:

```python
from db.models import Channel, Filter, Message, Notification, User, Vacancy
from db.session import AsyncSessionLocal
from models.schemas import PostExtraction, UserFilter
```

В `log_notification` (`db/repository.py:159-184`) добавить параметр `matched_vacancy_ids`:

```python
async def log_notification(
    *,
    user_id: int,
    message_id: int,
    success: bool,
    error: str | None = None,
    filter_id: int | None = None,
    matched_vacancy_ids: list[int] | None = None,
) -> bool:
    """Записать уведомление. Возвращает True, если запись создана,
    False если уже было (дубль) — это и есть наш дедуп."""
    async with AsyncSessionLocal() as session:
        try:
            session.add(
                Notification(
                    user_id=user_id,
                    message_id=message_id,
                    filter_id=filter_id,
                    success=success,
                    error=error,
                    matched_vacancy_ids=matched_vacancy_ids,
                )
            )
            await session.commit()
            return True
        except IntegrityError:
            await session.rollback()
            return False
```

- [ ] **Step 3: Sanity-check импортов**

Run: `python -c "from db.repository import insert_message_with_vacancies, log_notification; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add db/repository.py
git commit -m "feat(repo): insert_message_with_vacancies + matched_vacancy_ids on notifications"
```

---

### Task 9: Матчинг по вакансиям — `db/matching.py`

**Files:**
- Modify: `db/matching.py`
- Test: `tests/test_matching.py`

- [ ] **Step 1: Написать тесты на `matches(profile, post, vacancy)`**

`tests/test_matching.py`:

```python
"""Юнит-тесты per-vacancy matching. Используем простые объекты,
имитирующие ActorProfile (без БД)."""
from __future__ import annotations

from dataclasses import dataclass, field

from db.matching import matches
from models.schemas import PostExtraction, VacancyExtraction


@dataclass
class FakeProfile:
    gender: str | None = None
    play_age_min: int | None = None
    play_age_max: int | None = None
    project_types: list[str] = field(default_factory=list)
    role_types: list[str] = field(default_factory=list)
    min_rate: int | None = None
    city: str | None = None
    ready_for_travel: bool = False


def _post(**kw) -> PostExtraction:
    return PostExtraction(is_casting=True, confidence=0.9, **kw)


def _v(**kw) -> VacancyExtraction:
    return VacancyExtraction(**kw)


def test_match_basic_age_overlap():
    p = _post()
    v = _v(age_min=20, age_max=30)
    prof = FakeProfile(play_age_min=25, play_age_max=35)
    assert matches(prof, p, v) is True


def test_no_match_age_disjoint():
    p = _post()
    v = _v(age_min=8, age_max=10)
    prof = FakeProfile(play_age_min=25, play_age_max=35)
    assert matches(prof, p, v) is False


def test_match_one_of_many_vacancies():
    """Анкета 35-летней женщины, в посте 2 вакансии: подходит только одна."""
    p = _post(project_types=["kino_serial"], city="Москва")
    v_mama = _v(role_types=["main"], gender="female",
                age_min=35, age_max=45, rate=8000)
    v_son  = _v(role_types=["episode"], gender="male",
                age_min=8, age_max=10, rate=5000)
    prof = FakeProfile(
        gender="female", play_age_min=33, play_age_max=40,
        project_types=["kino_serial"], role_types=["main"],
        min_rate=5000, city="Москва",
    )
    assert matches(prof, p, v_mama) is True
    assert matches(prof, p, v_son) is False


def test_post_level_city_filter():
    p = _post(city="Москва")
    v = _v(age_min=20, age_max=30)
    prof = FakeProfile(play_age_min=25, play_age_max=35, city="Казань")
    assert matches(prof, p, v) is False


def test_post_level_city_filter_ready_for_travel():
    p = _post(city="Москва")
    v = _v(age_min=20, age_max=30)
    prof = FakeProfile(
        play_age_min=25, play_age_max=35, city="Казань", ready_for_travel=True,
    )
    assert matches(prof, p, v) is True


def test_rate_below_user_minimum():
    p = _post()
    v = _v(rate=3000)
    prof = FakeProfile(min_rate=10000)
    assert matches(prof, p, v) is False


def test_project_types_intersection_post_level():
    p = _post(project_types=["advertising"])
    v = _v()
    prof = FakeProfile(project_types=["kino_serial"])
    assert matches(prof, p, v) is False


def test_role_types_intersection_vacancy_level():
    p = _post()
    v = _v(role_types=["dancer"])
    prof = FakeProfile(role_types=["main"])
    assert matches(prof, p, v) is False


def test_unspecified_fields_pass_through():
    """Поле не указано в посте/вакансии → фильтр по нему не применяется."""
    p = _post()
    v = _v()  # пусто
    prof = FakeProfile()
    assert matches(prof, p, v) is True
```

- [ ] **Step 2: Запустить — упадёт** (старый matches принимает `ExtractedData`)

Run: `pytest tests/test_matching.py -v`

- [ ] **Step 3: Переписать `db/matching.py`**

```python
"""Сопоставление извлечённого объявления с анкетами пользователей."""
from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.models import ActorProfile, Message, Vacancy
from db.session import AsyncSessionLocal
from models.schemas import PostExtraction, VacancyExtraction

# Минимальная уверенность LLM для рассылки. Ниже — игнорируем сообщение.
MIN_CONFIDENCE = 0.5


def _ranges_overlap(a_lo: int, a_hi: int, b_lo: int, b_hi: int) -> bool:
    return not (a_hi < b_lo or a_lo > b_hi)


def _intersect(a: Iterable[str], b: Iterable[str]) -> bool:
    return bool(set(a) & set(b))


def matches(profile: ActorProfile, post: PostExtraction, vacancy: VacancyExtraction) -> bool:
    """True, если анкета подходит под конкретную вакансию в этом посте.

    project_types и city берём с уровня поста (общие);
    gender / age / role_types / rate — с уровня вакансии.
    Если параметр не указан в объявлении — фильтр по нему не применяется.
    """
    # Пол (per-vacancy)
    if vacancy.gender and profile.gender and vacancy.gender != profile.gender:
        return False

    # Возраст (per-vacancy)
    if vacancy.age_min is not None or vacancy.age_max is not None:
        msg_lo = vacancy.age_min if vacancy.age_min is not None else 0
        msg_hi = vacancy.age_max if vacancy.age_max is not None else 120
        prof_lo = profile.play_age_min if profile.play_age_min is not None else 0
        prof_hi = profile.play_age_max if profile.play_age_max is not None else 120
        if not _ranges_overlap(msg_lo, msg_hi, prof_lo, prof_hi):
            return False

    # Типы проектов (post-level)
    if post.project_types and profile.project_types:
        if not _intersect(post.project_types, profile.project_types):
            return False

    # Типы ролей (per-vacancy)
    if vacancy.role_types and profile.role_types:
        if not _intersect(vacancy.role_types, profile.role_types):
            return False

    # Ставка (per-vacancy)
    if vacancy.rate is not None and profile.min_rate is not None and vacancy.rate < profile.min_rate:
        return False

    # Город (post-level), с поправкой на ready_for_travel
    if post.city and profile.city:
        if post.city.lower() != profile.city.lower() and not profile.ready_for_travel:
            return False

    return True


async def find_matching_vacancies(
    post: PostExtraction,
    vacancies: list[VacancyExtraction],
) -> dict[int, list[int]]:
    """Возвращает {user_id: [индексы подошедших вакансий в списке `vacancies`]}.

    Гейтим по is_casting/confidence на уровне поста.
    Учитываем только анкеты с completed_at IS NOT NULL.
    Индексы соответствуют позициям в `vacancies`, что 1-в-1 совпадает с idx
    в БД, потому что Vacancy сохраняется с idx=enumerate(vacancies).
    """
    if not post.is_casting or post.confidence < MIN_CONFIDENCE or not vacancies:
        return {}

    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(ActorProfile).where(ActorProfile.completed_at.is_not(None))
        )
        profiles = res.scalars().all()

    out: dict[int, list[int]] = {}
    for p in profiles:
        hit_idxs = [i for i, v in enumerate(vacancies) if matches(p, post, v)]
        if hit_idxs:
            out[p.user_id] = hit_idxs
    return out
```

- [ ] **Step 4: Запустить тесты**

Run: `pytest tests/test_matching.py -v`
Expected: все 9 PASS

- [ ] **Step 5: Commit**

```bash
git add db/matching.py tests/test_matching.py
git commit -m "feat(matching): per-vacancy matches() + find_matching_vacancies()"
```

---

### Task 10: Рассылка — `userbot/client.py`

**Files:**
- Modify: `userbot/client.py`
- Test: `tests/test_notification_format.py`

- [ ] **Step 1: Тест на формат уведомления**

`tests/test_notification_format.py`:

```python
"""Юнит-тест на _format_notification: одна агрегированная карточка
со списком подошедших ролей."""
from __future__ import annotations

from dataclasses import dataclass

from models.schemas import PostExtraction, VacancyExtraction
from userbot.client import Userbot


@dataclass
class FakeMsg:
    id: int = 42
    message: str = "raw text"


def _post() -> PostExtraction:
    return PostExtraction(
        is_casting=True,
        project_types=["kino_serial"],
        city="Москва",
        summary="Сериал «X» — кастинг",
        confidence=0.9,
    )


def test_format_two_matched_vacancies():
    post = _post()
    vacancies = [
        VacancyExtraction(role_types=["main"], gender="female",
                          age_min=35, age_max=45, rate=8000,
                          description="Мама", role_label="Мама"),
        VacancyExtraction(role_types=["episode"], gender="male",
                          age_min=8, age_max=10, rate=5000,
                          description="Сын", role_label="Сын"),
    ]
    txt = Userbot._format_notification(
        post=post, vacancies=vacancies, matched_idxs=[0, 1],
        message=FakeMsg(), chat_username="castings_ch",
    )
    assert "Подходящий кастинг" in txt
    assert "Мама" in txt
    assert "Сын" in txt
    assert "8000" in txt
    assert "5000" in txt
    assert "Москва" in txt
    assert "https://t.me/castings_ch/42" in txt


def test_format_one_matched_vacancy_role_label_fallback():
    """Без role_label — карточка не должна показывать тех. код."""
    post = _post()
    vacancies = [
        VacancyExtraction(role_types=["main"], gender="female",
                          age_min=20, age_max=25, rate=5000,
                          description="Главная героиня"),
    ]
    txt = Userbot._format_notification(
        post=post, vacancies=vacancies, matched_idxs=[0],
        message=FakeMsg(), chat_username=None,
    )
    # Не должно быть голого "main" в карточке
    assert "main" not in txt.split("Открыть")[0]
    # Должен быть либо description, либо русский label роли
    assert "героин" in txt.lower() or "Главная" in txt
```

- [ ] **Step 2: Запустить — упадёт**

Run: `pytest tests/test_notification_format.py -v`

- [ ] **Step 3: Переписать `userbot/client.py`**

Полная замена файла:

```python
"""Telethon-userbot: слушает каналы, парсит сообщения через LLM,
пишет историю в БД и рассылает совпадения подходящим анкетам."""
from __future__ import annotations

import asyncio
from pathlib import Path

from aiogram import Bot
from loguru import logger
from telethon import TelegramClient, events

from api.reference_data import all_refs
from config import settings
from db import matching, repository
from llm.base import LLMProvider
from models.schemas import PostExtraction, VacancyExtraction

_REFS = all_refs()
_PROJECT_LABELS = {it["code"]: it["label"] for it in _REFS["project_types"]}
_ROLE_LABELS = {it["code"]: it["label"] for it in _REFS["role_types"]}


def _labels(codes: list[str], mapping: dict[str, str]) -> str:
    if not codes:
        return "—"
    return ", ".join(mapping.get(c, c) for c in codes)


def _format_age(v: VacancyExtraction) -> str:
    if v.age_min is not None and v.age_max is not None:
        return f"{v.age_min}" if v.age_min == v.age_max else f"{v.age_min}–{v.age_max}"
    if v.age_min is not None:
        return f"от {v.age_min}"
    if v.age_max is not None:
        return f"до {v.age_max}"
    return "—"


def _vacancy_title(v: VacancyExtraction) -> str:
    """role_label если есть → русский label из справочника → 'Роль'."""
    if v.role_label:
        return v.role_label
    if v.role_types:
        return _ROLE_LABELS.get(v.role_types[0], v.role_types[0])
    return "Роль"


class Userbot:
    def __init__(
        self,
        llm: LLMProvider,
        bot: Bot,
        session_dir: str | Path = "sessions",
    ):
        self.llm = llm
        self.bot = bot
        Path(session_dir).mkdir(parents=True, exist_ok=True)
        self.client = TelegramClient(
            str(Path(session_dir) / settings.tg_session_name),
            settings.tg_api_id,
            settings.tg_api_hash,
        )

    async def _resolve_channels(self) -> list:
        await repository.seed_channels_if_empty(settings.tg_channels, added_by=0)
        rows = await repository.list_channels(active_only=True)
        usernames = [f"@{r.username}" for r in rows]

        if not usernames:
            logger.warning("Нет активных каналов в БД — userbot работает «вхолостую»")
            return []

        entities = []
        for ch in usernames:
            try:
                entity = await self.client.get_entity(ch)
                entities.append(entity)
                logger.info("Подписан на канал {} (id={})", ch, getattr(entity, "id", "?"))
            except Exception as e:  # noqa: BLE001
                logger.error("Не удалось получить entity для {}: {}", ch, e)
        return entities

    @staticmethod
    def _format_notification(
        *,
        post: PostExtraction,
        vacancies: list[VacancyExtraction],
        matched_idxs: list[int],
        message,
        chat_username: str | None,
    ) -> str:
        """Карточка для пользователя. Перечисляет только подошедшие вакансии."""
        link = ""
        if chat_username:
            link = f"https://t.me/{chat_username}/{message.id}"

        lines: list[str] = [
            "<b>🎬 Подходящий кастинг</b>",
            f"Тип проекта: {_labels(post.project_types, _PROJECT_LABELS)} | "
            f"Город: {post.city or '—'}",
            f"<b>Подходящие роли ({len(matched_idxs)}):</b>",
        ]
        for idx in matched_idxs:
            v = vacancies[idx]
            gender_ru = {"male": "м", "female": "ж"}.get(v.gender or "", "—")
            rate_str = f"{v.rate} ₽" if v.rate is not None else "ставка не указана"
            lines.append(
                f"• <b>{_vacancy_title(v)}</b> — {_format_age(v)}, {gender_ru}, {rate_str}"
            )

        lines.append("")
        lines.append(post.summary or (message.message or "")[:300])
        if link:
            lines.append(f"\n<a href=\"{link}\">Открыть сообщение</a>")
        return "\n".join(lines)

    async def _handle_message(self, event):
        text = (event.message.message or "").strip()
        if not text:
            return
        logger.debug("Новое сообщение: {!r}", text[:120])

        post = await self.llm.extract(text)
        logger.info(
            "LLM extract: casting={} project={} city={} vacancies={} conf={:.2f}",
            post.is_casting, post.project_types, post.city,
            len(post.vacancies), post.confidence,
        )

        chat = event.message.chat
        chat_id = getattr(chat, "id", 0)
        chat_username = getattr(chat, "username", None)
        message_db_id, vacancy_ids = await repository.insert_message_with_vacancies(
            tg_chat_id=chat_id,
            tg_chat_username=chat_username,
            tg_message_id=event.message.id,
            text=text,
            extracted=post,
        )
        if message_db_id is None:
            return

        # Ничего не матчим, если пост отбракован или вакансий нет
        if not post.is_casting or not vacancy_ids or not post.vacancies:
            return

        user_to_idxs = await matching.find_matching_vacancies(post, post.vacancies)
        if not user_to_idxs:
            logger.debug("Нет подходящих анкет для сообщения {}", message_db_id)
            return

        for user_id, hit_idxs in user_to_idxs.items():
            if await repository.already_notified(user_id, message_db_id):
                continue

            notification_text = self._format_notification(
                post=post, vacancies=post.vacancies,
                matched_idxs=hit_idxs,
                message=event.message, chat_username=chat_username,
            )
            matched_db_ids = [vacancy_ids[i] for i in hit_idxs]

            success = False
            err: str | None = None
            try:
                await self.bot.send_message(
                    user_id,
                    notification_text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
                success = True
            except Exception as e:  # noqa: BLE001
                err = str(e)
                logger.warning("Не удалось отправить пользователю {}: {}", user_id, e)

            await repository.log_notification(
                user_id=user_id,
                message_id=message_db_id,
                success=success,
                error=err,
                matched_vacancy_ids=matched_db_ids,
            )
            await asyncio.sleep(0.05)

    async def start(self) -> None:
        await self.client.start(phone=settings.tg_phone)
        entities = await self._resolve_channels()
        if not entities:
            logger.warning(
                "Список каналов пуст или ни один не разрешился — userbot работает «вхолостую»"
            )

        @self.client.on(events.NewMessage(chats=entities or None))
        async def _handler(event):  # noqa: ANN001
            await self._handle_message(event)

        logger.info(
            "Userbot запущен, слушаю каналы: {}",
            [getattr(e, "username", getattr(e, "id", "?")) for e in entities],
        )
        await self.client.run_until_disconnected()
```

- [ ] **Step 4: Запустить тесты на формат**

Run: `pytest tests/test_notification_format.py -v`
Expected: оба PASS

- [ ] **Step 5: Прогнать ВСЕ тесты, чтобы убедиться, что ничего не сломали**

Run: `pytest tests/ -v`
Expected: все тесты PASS

- [ ] **Step 6: Commit**

```bash
git add userbot/client.py tests/test_notification_format.py
git commit -m "feat(userbot): per-vacancy matching + aggregated notification card"
```

---

### Task 11: Админка — `api/admin.py` + webapp

**Files:**
- Modify: `api/admin.py`
- Modify: `webapp/src/types.ts`
- Modify: `webapp/src/components/AdminDashboard.tsx`

- [ ] **Step 1: Обновить `api/admin.py`**

Добавить схему `AdminVacancy` и поле `vacancies` в `AdminMessage`. Импорты в `api/admin.py:16-17`:

```python
from sqlalchemy.orm import selectinload

from db.models import ActorProfile, Message, Notification, Vacancy
```

Добавить класс перед `AdminMessage` (`api/admin.py:37`):

```python
class AdminVacancy(BaseModel):
    id: int
    idx: int
    role_types: list[str] = []
    gender: Optional[str] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    rate: Optional[int] = None
    description: Optional[str] = None
    role_label: Optional[str] = None
```

В `AdminMessage` добавить поле:

```python
    vacancies: list[AdminVacancy] = []
```

В `list_messages` (`api/admin.py:128`) изменить запрос:

```python
        msg_stmt = (
            select(Message)
            .options(selectinload(Message.vacancies))
            .order_by(Message.id.desc())
            .limit(limit)
            .offset(offset)
        )
```

И в построении `AdminMessage` (`api/admin.py:152-170`) добавить поле:

```python
        AdminMessage(
            id=m.id,
            tg_chat_username=m.tg_chat_username,
            tg_message_id=m.tg_message_id,
            text=m.text,
            is_casting=m.is_casting,
            gender=m.gender,
            age_min=m.age_min,
            age_max=m.age_max,
            project_types=list(m.project_types or []),
            role_types=list(m.role_types or []),
            city=m.city,
            rate=m.rate,
            summary=m.summary,
            confidence=m.confidence,
            received_at=m.received_at,
            notified_count=notif_counts.get(m.id, 0),
            vacancies=[
                AdminVacancy(
                    id=v.id, idx=v.idx,
                    role_types=list(v.role_types or []),
                    gender=v.gender, age_min=v.age_min, age_max=v.age_max,
                    rate=v.rate, description=v.description, role_label=v.role_label,
                )
                for v in m.vacancies
            ],
        )
```

- [ ] **Step 2: Обновить `webapp/src/types.ts`**

После определения `AdminMessageRow` добавить:

```typescript
export interface AdminVacancyRow {
  id: number;
  idx: number;
  role_types: string[];
  gender: string | null;
  age_min: number | null;
  age_max: number | null;
  rate: number | null;
  description: string | null;
  role_label: string | null;
}
```

И в `AdminMessageRow` добавить поле:

```typescript
  vacancies: AdminVacancyRow[];
```

- [ ] **Step 3: Обновить рендер в `webapp/src/components/AdminDashboard.tsx`**

В `MessagesTab` (после блока с post-level метаданными, `webapp/src/components/AdminDashboard.tsx:208-231`) добавить:

```tsx
              {m.vacancies.length > 0 && (
                <div className="mt-2 space-y-1">
                  <div className="text-xs text-slate-500">
                    Вакансии ({m.vacancies.length}):
                  </div>
                  <ul className="space-y-1">
                    {m.vacancies.map((v) => (
                      <li
                        key={v.id}
                        className="text-xs text-slate-300 bg-bg-card rounded px-2 py-1"
                      >
                        <span className="font-medium">
                          {v.role_label ?? v.role_types[0] ?? "Роль"}
                        </span>
                        {v.gender && <> · {v.gender === "male" ? "м" : "ж"}</>}
                        {v.age_min != null && (
                          <>
                            {" "}
                            · {v.age_min}
                            {v.age_max !== v.age_min ? `–${v.age_max}` : ""} лет
                          </>
                        )}
                        {v.rate != null && (
                          <> · {v.rate.toLocaleString("ru-RU")} ₽</>
                        )}
                        {v.role_types.length > 0 && (
                          <> · {v.role_types.join(",")}</>
                        )}
                        {v.description && (
                          <div className="text-slate-400 mt-0.5 break-words">
                            {v.description}
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
```

- [ ] **Step 4: Sanity-check API-импортов**

Run: `python -c "from api.admin import AdminVacancy, AdminMessage; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Сборка webapp** (если есть локальная node-окружение)

Run: `cd webapp && npm run build`
Expected: build OK без TS-ошибок. Если node не установлен локально — пропустить, проверим в CI/dev-стенде.

- [ ] **Step 6: Commit**

```bash
git add api/admin.py webapp/src/types.ts webapp/src/components/AdminDashboard.tsx
git commit -m "feat(admin): expose vacancies in /api/admin/messages + webapp render"
```

---

### Task 12: Чистка `filters/storage.py`

`FilterStorage.find_matches` уже сломан (вызывает несуществующий `f.matches(...)`) и нигде не используется. Чтобы не плодить технический долг и не ломать импорты, переводим параметр на новый тип, а тело метода оставляем как «no-op», явно помеченным deprecation-варнингом.

**Files:**
- Modify: `filters/storage.py`

- [ ] **Step 1: Обновить `filters/storage.py`**

Полная замена:

```python
"""Хранилище фильтров на PostgreSQL.

Сохраняем тот же интерфейс, что был у JSON-варианта, чтобы остальной код
(userbot, bot/handlers) не пришлось переписывать. По смыслу — это адаптер
поверх db/repository.py."""
from __future__ import annotations

from typing import Iterable

from loguru import logger

from db import repository
from models.schemas import PostExtraction, UserFilter


class FilterStorage:
    """Тонкая обёртка над репозиторием. Пока — один фильтр на пользователя."""

    def __init__(self, *_args, **_kwargs):
        pass

    async def upsert(self, f: UserFilter) -> None:
        await repository.upsert_single_filter(f)

    async def remove(self, user_id: int) -> bool:
        deleted = await repository.remove_filters(user_id)
        return deleted > 0

    async def get(self, user_id: int) -> UserFilter | None:
        return await repository.get_user_filter(user_id)

    async def all(self) -> list[UserFilter]:
        return await repository.all_filters()

    async def find_matches(self, extracted: PostExtraction) -> Iterable[UserFilter]:
        """Deprecated: матчинг переехал в db.matching.find_matching_vacancies.
        Здесь оставлено как no-op, чтобы не ломать исторические импорты."""
        logger.warning(
            "FilterStorage.find_matches is deprecated; use db.matching.find_matching_vacancies"
        )
        return []
```

- [ ] **Step 2: Sanity-check**

Run: `python -c "from filters.storage import FilterStorage; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add filters/storage.py
git commit -m "refactor: retype FilterStorage.find_matches to PostExtraction (deprecated no-op)"
```

---

### Task 13: Накат миграции и end-to-end smoke

**Files:** (только проверочные действия, файлы не меняем)

- [ ] **Step 1: Поднять локальную БД** (если ещё не запущена)

Run: `docker compose up -d postgres`
Expected: контейнер `tg_parser_postgres` в состоянии `healthy`.

- [ ] **Step 2: Накатить все миграции на чистой БД**

Run: `alembic upgrade head`
Expected: stdout содержит `Running upgrade 0006_messages_casting -> 0007_vacancies`. Без ошибок.

- [ ] **Step 3: Проверить структуру**

Run:
```bash
docker exec tg_parser_postgres psql -U tg_parser -d tg_parser \
  -c "\d vacancies" \
  -c "\d notifications"
```
Expected: таблица `vacancies` со всеми колонками и `uq_vacancies_message_idx`; в `notifications` есть `matched_vacancy_ids` (integer[]).

- [ ] **Step 4: Проверить, что бэкфилл сработал бы на исторических данных**

Если в локальной БД нет старых сообщений — пропустить. Если есть:

```bash
docker exec tg_parser_postgres psql -U tg_parser -d tg_parser -c "
SELECT COUNT(*) AS messages_casting FROM messages WHERE is_casting = true;
SELECT COUNT(*) AS vacancies_total FROM vacancies;
SELECT COUNT(*) AS distinct_msgs FROM (SELECT DISTINCT message_id FROM vacancies) s;
"
```
Expected: `messages_casting == distinct_msgs`, `vacancies_total == messages_casting` (по 1 вакансии на пост).

- [ ] **Step 5: End-to-end smoke с stub-провайдером**

Run: `python -c "
import asyncio
from llm.stub_provider import StubProvider
from db.repository import insert_message_with_vacancies

async def main():
    p = await StubProvider().extract('Кастинг на сериал. Девушка 25-30 лет.')
    print('extracted:', p.model_dump())
    msg_id, vac_ids = await insert_message_with_vacancies(
        tg_chat_id=999_999, tg_chat_username='smoke',
        tg_message_id=1, text='Кастинг на сериал. Девушка 25-30 лет.',
        extracted=p,
    )
    print('msg_id:', msg_id, 'vac_ids:', vac_ids)

asyncio.run(main())
"`

Expected: вывод вида `extracted: {... vacancies: [{...}]}` и `msg_id: 1 vac_ids: [1]`.

- [ ] **Step 6: Прогнать полный pytest ещё раз**

Run: `pytest tests/ -v`
Expected: все тесты из Task 2/3/4/5/9/10 PASS.

- [ ] **Step 7: Commit smoke-тег пустой коммит-меткой** (опционально, чтобы зафиксировать момент проверки)

```bash
git commit --allow-empty -m "chore: verify multi-vacancy migration + smoke OK"
```

---

## Self-review (выполнено автором плана)

**Spec coverage**

- Vacancies table → Task 6 + Task 7 ✓
- PostExtraction / VacancyExtraction → Task 2 ✓
- Per-vacancy normalization → Task 3 ✓
- Updated LLM prompt → Task 4 ✓
- Stub provider adaptation → Task 5 ✓
- `insert_message_with_vacancies` → Task 8 ✓
- `find_matching_vacancies` + per-vacancy `matches` → Task 9 ✓
- Aggregated notification card + dedup `(user_id, message_id)` → Task 10 ✓
- `notifications.matched_vacancy_ids` → Task 6 (model) + Task 7 (migration) + Task 8 (write) + Task 10 (populate) ✓
- Migration with backfill → Task 7 ✓
- Admin endpoint + webapp render → Task 11 ✓
- Removal of `ExtractedData` (clean cut, no alias) → Task 2 covers; Task 12 retypes the last remaining import in `filters/storage.py` ✓
- Edge case: `is_casting=true` + empty `vacancies` → Task 4 (forces `is_casting=false`) ✓
- Out of scope (re-extract истории, удаление legacy-колонок, разделённые карточки) — НЕ включены, как и оговорено в спеке ✓

**Type consistency**

- `extract()` всюду возвращает `PostExtraction` (Task 2/4/5).
- `matches(profile, post, vacancy)` — единая сигнатура (Task 9), используется в `find_matching_vacancies` и в тестах.
- `insert_message_with_vacancies(..., extracted: PostExtraction) -> tuple[int|None, list[int]]` — единый возврат, потребляется в Task 10.
- `log_notification(matched_vacancy_ids=...)` — параметр добавлен в Task 8 и заполняется в Task 10.

**Placeholders**

- Все шаги содержат полный код / точные команды / ожидаемый output. TODO/TBD не остались.
