# Спецификация: матчинг под категории Event / General / Admin

**Дата:** 2026-05-08
**Автор:** Claude Opus 4.7
**Статус:** черновик, ожидает ревью пользователя

## Проблема

После PR #8 (mini-app категории) у юзеров есть 4 типа подписки —
`creative` / `event` / `general` / `admin`. Но матчер вакансий
(`db/matching.py`) и LLM-extract (`llm/base.py`) хардкоженно работают
только под creative (актёры/модели). Юзеры с подписками на event,
general, admin регистрируются, заполняют анкету и **не получают
никаких уведомлений**.

## Цель

Расширить LLM-extract так, чтобы он определял категорию вакансии
(creative / event / general / admin) и извлекал `work_types`
для не-creative категорий. Расширить матчер на 4 per-category функции
с собственными правилами. Юзеры всех 4 категорий начинают получать
релевантные уведомления.

## Не цель

- Изменения в Mini App / профилях юзеров — анкеты уже расширены в PR #8.
- Уведомления старых юзеров о смене анкеты (отдельный спек).
- Удаление legacy `actor_profile` таблицы и старого UI кода (отдельный
  спек по техдолгу).
- Race-fix для дедупа на бёрст-окне (PR #15 покрыл основной race; bursts
  обрабатываются UNIQUE на нотификациях, отдельный спек на cleanup).

## Принятые решения

1. **Уровень категории — гибрид (Variant C).** `Message.category`
   обязательное (доминирующая категория поста), `Vacancy.category`
   опциональное (override для редких гибрид-постов вроде «2 хостес +
   фотомодель»). Match-логика: `effective_cat = vacancy.category or
   message.category`.
2. **Возраст:** для creative матчим по `play_age_min/max` (играемый),
   для не-creative — по `actual_age` (актуальный, single value).
3. **Физические параметры (height, body_type, hair, ethnicity)** —
   опциональны во vacancy. Если LLM их извлёк — фильтруем; если
   пусто — не фильтруем.
4. **`physical_fitness` (general) и `education` (admin) НЕ участвуют
   в матчинге.** Поля остаются на уровне `*Profile` для UI/будущего,
   но `VacancyExtraction` их не извлекает и матчер не учитывает.
5. **Бэкфилл существующих row'ов:** в миграции
   `UPDATE messages SET category = 'creative' WHERE is_casting = TRUE`
   — это правда, потому что LLM до миграции извлекал только creative.

## Архитектура

```
LLM-extract → PostExtraction(category, vacancies[VacancyExtraction(category?, work_types[]...)])
       │
       ▼
insert_message_with_vacancies → messages.category, vacancies.category, vacancies.work_types
       │
       ▼
find_matching_vacancies(post, vacancies):
   for vacancy:
     effective_cat = vacancy.category or post.category
     matcher = CATEGORY_MATCHERS[effective_cat]
     users = await matcher(post, vacancy)
       │
       ▼
   _match_creative / _match_event / _match_general / _match_admin
       (каждая загружает свою *Profile + фильтрует по subscription)
       │
       ▼
   notification → text_hash UNIQUE отсекает уже-уведомлённых
```

## Расширение LLM-схемы

### `models/schemas.py`

```python
CategoryCode = Literal["creative", "event", "general", "admin"]

class PostExtraction(BaseModel):
    is_casting: bool
    category: Optional[CategoryCode] = None       # NEW: доминирующая категория
    project_types: list[str] = []                 # релевантно для creative
    city: Optional[str] = None
    summary: Optional[str] = None
    confidence: float = 0.0
    vacancies: list[VacancyExtraction] = []

class VacancyExtraction(BaseModel):
    role_types: list[str] = []                    # creative
    work_types: list[str] = []                    # NEW: event/general/admin
    category: Optional[CategoryCode] = None       # NEW: override для гибрид-постов
    gender: Optional[Literal["male","female"]] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    rate: Optional[int] = None
    ethnicity: list[str] = []                     # creative + event (опц.)
    height_min: Optional[int] = None              # creative + event (опц.)
    height_max: Optional[int] = None
    body_type: list[str] = []                     # creative + event (опц.)
    hair_color: list[str] = []                    # creative + event (опц.)
    hair_length: list[str] = []                   # creative + event (опц.)
    description: Optional[str] = None
    role_label: Optional[str] = None
```

### `llm/base.py:SYSTEM_PROMPT` — расширение

Добавляются 4 секции:

1. **Описание 4 категорий** с маркерами:
   - `creative` — кастинги в кино, рекламу, театр; роли: актёр, модель, фотомодель.
   - `event` — мероприятия; роли: хостес, промо-модель, аниматор.
   - `general` — разнорабочие; роли: хелпер, клининг, грузчик.
   - `admin` — оператор регистрации, супервайзер на event-площадках.

2. **Правило для `post.category`:** «определи доминирующую категорию по тексту; если пост явно не про работу или категория не входит в перечень — оставь null».

3. **Правила для `work_types` per category** (enum-значения):
   - event: `hostess`, `promo_model`, `animator`
   - general: `helper`, `cleaning`, `loader`
   - admin: `registration_operator`, `supervisor`

4. **Правило для `vacancy.category` override:** «только если конкретная роль явно не из доминирующей категории. Иначе оставь null (наследование от поста)».

Для creative-вакансий в JSON-выводе LLM продолжает заполнять `role_types`, для event/general/admin — `work_types` (а `role_types` пустое).

### `llm/normalize.py`

`normalize_extracted` валидирует `category` ∈ enum + чистит unknown коды в `work_types` против per-category whitelist.

## Расширение БД

### Миграция 0016

```sql
ALTER TABLE messages
  ADD COLUMN category VARCHAR(16) NULL;
ALTER TABLE messages
  ADD CONSTRAINT ck_messages_category
    CHECK (category IS NULL OR category IN ('creative','event','general','admin'));

ALTER TABLE vacancies
  ADD COLUMN category VARCHAR(16) NULL,
  ADD COLUMN work_types TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE vacancies
  ADD CONSTRAINT ck_vacancies_category
    CHECK (category IS NULL OR category IN ('creative','event','general','admin'));

CREATE INDEX ix_messages_category ON messages (category) WHERE category IS NOT NULL;

-- Бэкфилл: исторические casting-посты — все creative.
UPDATE messages SET category = 'creative' WHERE is_casting = TRUE;
```

### `db/models.py`

`Message.category` (String(16), nullable), `Vacancy.category` (String(16),
nullable), `Vacancy.work_types` (ARRAY(Text), default=list,
server_default="{}", nullable=False).

## Reference data

`api/reference_data.py` добавляет 3 новых справочника:

```python
WORK_TYPES_EVENT = [
    {"code": "hostess", "label": "Хостес"},
    {"code": "promo_model", "label": "Промо-модель"},
    {"code": "animator", "label": "Аниматор"},
]
WORK_TYPES_GENERAL = [
    {"code": "helper", "label": "Хелпер"},
    {"code": "cleaning", "label": "Клининг"},
    {"code": "loader", "label": "Грузчик"},
]
WORK_TYPES_ADMIN = [
    {"code": "registration_operator", "label": "Оператор регистрации"},
    {"code": "supervisor", "label": "Супервайзер"},
]
```

`/api/refs` возвращает их под ключами `work_types_event`,
`work_types_general`, `work_types_admin`. Pydantic-валидаторы в
`api/schemas.py` (`_VALID_EVENT_WORK_TYPES` и аналоги) переходят на эти
справочники как single source of truth, фронт перестаёт хардкодить
лейблы.

## Матчер

`db/matching.py` реструктурируется. Текущая `matches(profile, post,
vacancy)` переименовывается в `_match_creative_check` (внутренний
helper). Появляется dispatch-таблица:

```python
CATEGORY_MATCHERS = {
    "creative": _match_creative,
    "event":    _match_event,
    "general":  _match_general,
    "admin":    _match_admin,
}

async def find_matching_vacancies(
    post: PostExtraction,
    vacancies: list[VacancyExtraction],
) -> dict[int, list[int]]:
    if not post.is_casting or post.confidence < MIN_CONFIDENCE:
        return {}
    out: dict[int, list[int]] = {}
    for idx, v in enumerate(vacancies):
        eff_cat = v.category or post.category
        matcher = CATEGORY_MATCHERS.get(eff_cat) if eff_cat else None
        if matcher is None:
            continue  # категория не определена — никому
        user_ids = await matcher(post, v)
        for uid in user_ids:
            out.setdefault(uid, []).append(idx)
    return out
```

Каждая `_match_<cat>` функция:
1. Загружает соответствующую `*Profile` через `select(Profile).join(UserCategorySubscription).where(category=<cat>, enabled=True, completed_at IS NOT NULL)`.
2. Применяет per-category правила (см. ниже).
3. Возвращает `list[int]` — user_id'ы матчей.

### Правила per-category

**Общие гейты (применяются во всех 4 функциях):**
- `post.city == profile.city OR profile.ready_for_travel`
- `vacancy.rate ≥ profile.min_rate` (если оба указаны)
- `vacancy.gender == profile.gender` (если в vacancy указан)

**Creative (`_match_creative`):**
- `post.project_types ∩ profile.project_types`
- `vacancy.role_types ∩ profile.role_types`
- `vacancy.age_min/max` overlap `profile.play_age_min/max` ← **играемый**
- `vacancy.ethnicity ∩ profile.ethnicity` (если vacancy.ethnicity не пусто)
- `vacancy.height_min/max` contains `profile.height_cm` (если указаны)
- `vacancy.body_type ∩ profile.body_type` (если не пусто)
- `vacancy.hair_color ∋ profile.hair_color` (если не пусто)
- `vacancy.hair_length ∋ profile.hair_length` (если не пусто)

**Event (`_match_event`):**
- `vacancy.work_types ∩ profile.work_types` — обязательно (если оба не пусты, должно пересечься; если у vacancy work_types пуст — не фильтруем)
- `vacancy.age_min/max` overlap `profile.actual_age` ← **актуальный**
- `vacancy.ethnicity / height / body_type / hair_color / hair_length` — как в creative, опционально

**General (`_match_general`):**
- `vacancy.work_types ∩ profile.work_types` — обязательно
- `vacancy.age_min/max` overlap `profile.actual_age`
- НЕ используется: ethnicity, body_type, hair, role_types, project_types, physical_fitness

**Admin (`_match_admin`):**
- `vacancy.work_types ∩ profile.work_types` — обязательно
- `vacancy.age_min/max` overlap `profile.actual_age`
- НЕ используется: gender, ethnicity, body_type, hair, height, education

## Работа с уведомлениями

Userbot (`userbot/client.py`) не меняется. Текущий `_process_canonical`
вызывает `find_matching_vacancies(post, vacancies)` — теперь матчер
сам диспатчит. Нотификации с `text_hash` дедупом из PR #15 продолжают
работать как есть.

## Этапы реализации (для writing-plans)

1. **Миграция + ORM** (`0016_per_category_vacancies.py`,
   `db/models.py`).
2. **Pydantic схема + LLM-нормализация** (`models/schemas.py`,
   `llm/normalize.py`).
3. **LLM-промпт** (`llm/base.py:SYSTEM_PROMPT` расширение).
4. **Reference data + Pydantic-валидаторы** (`api/reference_data.py`,
   `api/schemas.py`).
5. **Матчер dispatch + 4 per-category функции** (`db/matching.py`)
   с тестами на каждую.
6. **Бэкфилл existing data + cutover-проверка** (миграция SQL +
   smoke-test deploy logs).

## Тесты

`tests/test_matching_creative.py` (рефакторинг существующих),
`tests/test_matching_event.py`, `_general.py`, `_admin.py` — pure-logic
тесты per-category на mocked ORM объектах. Покрытие: positive match,
gate failures (city, rate, gender, age, work_types intersection).

`tests/test_llm_normalize.py` обновляется под новые поля
(`category`, `work_types`).

## Риски

| Риск | Митигация |
|---|---|
| LLM плохо классифицирует категорию (особенно гибрид-посты) | Логируем `category` каждого extract; первые сутки после деплоя ручная проверка sample. Если систематические ошибки — улучшаем промпт. |
| LLM присваивает `null` категорию слишком часто (boundary cases) | Лучше null чем wrong: при null матчинг не идёт, юзер просто не получает; better miss than wrong notification. |
| Существующие creative-юзеры теряют уведомления при бэкфилле | Бэкфилл `category='creative'` для всех `is_casting=TRUE` — текущие посты сохраняют поведение. |
| `_match_event/general/admin` имеют баги первое время | Pure-logic тесты на каждый matcher до деплоя. |
| `physical_fitness` / `education` колонки в `*Profile` остаются неиспользуемыми | Принимаем — могут пригодиться позже; UI для них уже скрыт (PR #11). |

## Альтернативы (отклонено)

- **Variant A (Message-only category):** теряет редкие гибрид-посты (~5%). C даёт 100% покрытие за минимальный оверхед.
- **Two-step LLM (классификация + extract per-category):** дороже на токены и медленнее. Достаточно one-shot с расширенным промптом.
- **Эвристика по keywords (без LLM-классификации):** хрупко, не справится с разнообразием формулировок.
- **Матчинг через JSONB-условия в SQL:** усложняет дебаг и эволюцию правил. Python-функция читаемее.
