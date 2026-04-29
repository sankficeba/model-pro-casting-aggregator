# Multi-vacancy extraction: один пост → несколько вакансий

**Статус:** дизайн утверждён, ждём ревью спеки перед тем, как писать план реализации.
**Дата:** 2026-04-29

## Проблема

Сейчас на одно Telegram-сообщение из канала кастингов приходится одна строка в таблице `messages` с одним набором полей: `gender`, `(age_min, age_max)`, `role_types`, `rate`, `summary`. Если в одном посте описано несколько ролей с разными условиями (пример: `messages.id = 16` — на проект ищут несколько разных ролей с разными гонорарами), LLM вынужден схлопнуть всё это в один «усреднённый» набор полей. Это:

- **Теряет информацию.** Возрастной диапазон расширяется до объединения (например, 8–45 вместо «мама 35–45 + сын 8–10»), ставка превращается в одно число при наличии 2–5 разных ставок.
- **Ломает матчинг.** `db/matching.py:matches()` сравнивает анкету с этой усреднённой картиной — пользователь либо получает уведомление «вообще про что-то из этого поста», либо не получает вообще, хотя одна из конкретных ролей идеально подходит.
- **Делает уведомления бесполезными.** Карточка показывает обобщённые цифры, по которым непонятно, на какую именно роль приглашают.

## Цель

Изменить логику извлечения и хранения так, чтобы каждая вакансия из поста хранилась отдельно со своими условиями, и матчинг/уведомления работали по конкретным вакансиям.

## Дизайн

### Архитектура: пост vs. вакансия

Разводим два уровня:

- **Пост (`messages`)** — то, что прилетело из Telegram. Один пост = одна строка. Содержит общие для всего поста данные.
- **Вакансия (`vacancies`)** — одна роль, описанная в посте, со своими условиями. Один пост → 0..N вакансий (0 — если `is_casting=false`).

| Уровень `messages` (пост) | Уровень `vacancies` (роль) |
|---|---|
| `text`, `tg_chat_id`, `tg_chat_username`, `tg_message_id`, `received_at` | `role_types` |
| `is_casting`, `confidence` | `gender` |
| `project_types` (тип проекта общий) | `age_min`, `age_max` |
| `city` (город съёмки общий) | `rate` |
| `summary` (общее краткое описание поста) | `description` (текст про эту конкретную роль) |
| | `role_label` (человекочитаемое имя роли — «Мама», «Сын») |
| | `idx` (порядок вакансии в посте) |

### Схема БД

#### Новая таблица `vacancies`

```python
class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    idx: Mapped[int] = mapped_column(Integer, nullable=False)  # порядок в посте: 0,1,2...
    role_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False,
    )
    gender: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    age_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    age_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role_label: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    __table_args__ = (
        UniqueConstraint("message_id", "idx", name="uq_vacancies_message_idx"),
    )
```

`idx` — стабильный порядок вакансии в посте; нужен для устойчивости к re-extract (UPSERT по `(message_id, idx)`) и для предсказуемого порядка в админке/уведомлениях.

`role_label` — короткое имя роли, как написано в посте («Мама», «Прохожий №3»). `role_types` — нормализованный код для матчинга. Без `role_label` уведомления показывали бы технические коды вместо человеческих имён.

#### Изменения в `messages`

Колонки `gender`, `age_min`, `age_max`, `role_types`, `rate` физически остаются — для безопасного rollback и для исторических данных. Новый код их **не читает и не пишет**, как сейчас обстоит дело с legacy-полями `age` и `category`. Удалить колонки можно отдельной чисткой позже.

#### Изменения в `notifications`

Добавляется `matched_vacancy_ids: ARRAY(Integer) | None` — какие именно вакансии попали в карточку. Нужно для отладки и для будущей фичи «нашлась ещё одна роль из того же поста». `UniqueConstraint(user_id, message_id)` — остаётся как есть.

### Pydantic-схемы

`models/schemas.py`:

```python
class VacancyExtraction(BaseModel):
    role_types: list[str] = []
    gender: Optional[Literal["male", "female"]] = None
    age_min: Optional[int] = Field(None, ge=0, le=120)
    age_max: Optional[int] = Field(None, ge=0, le=120)
    rate: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    role_label: Optional[str] = None

class PostExtraction(BaseModel):
    is_casting: bool = False
    project_types: list[str] = []
    city: Optional[str] = None
    summary: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    vacancies: list[VacancyExtraction] = []
```

`ExtractedData` удаляем целиком — все три места, которые её читают (`db/repository.py:insert_message`, `db/matching.py:matches`, `userbot/client.py:_format_notification`), всё равно переписываются под новую схему. Алиас бы только маскировал, что callers не подходят под новую модель.

### LLM-промпт

`llm/base.py:SYSTEM_PROMPT` переписывается. Ключевые правила:

- Поля верхнего уровня (`is_casting`, `project_types`, `city`, `summary`, `confidence`) — про пост.
- `vacancies` — массив. Если пост — одна роль, массив длины 1. Если несколько — по записи на роль. Если `is_casting=false` — массив пустой.
- Для каждой вакансии: `role_types` (нормализованные коды), `role_label` (как названа в посте), `description` (фрагмент поста об этой роли), и индивидуальные `gender / age_min / age_max / rate`.
- На пустой/нераспарсенный ответ — `PostExtraction(confidence=0.0, vacancies=[])`.

`llm/normalize.py` применяет нормализацию и к `project_types` поста, и к `role_types` каждой вакансии.

### Поток данных

1. **Userbot ловит сообщение** (`userbot/client.py:_handle_message`).
2. **LLM extract** возвращает `PostExtraction`.
3. **`insert_message_with_vacancies(...)`** в одной транзакции:
   - UPSERT в `messages` по `(tg_chat_id, tg_message_id)` — как сейчас.
   - Если строка только что создана и `is_casting=true` — INSERT в `vacancies` со списком вакансий, `idx = 0..N-1`.
   - Если строка уже была (дубль из Telegram-ретрансляции) — вакансии не пересоздаём.
4. **Матчинг** (`db/matching.py`):
   - `is_casting`/`confidence` гейтят пост целиком — если пост отбракован, вакансии не считаем.
   - `find_matching_vacancies(post, vacancies, profiles)` → `dict[user_id, list[vacancy_id]]`.
   - `matches(profile, post, vacancy)`: пол / возраст / role_types / rate сверяем с `vacancy`; project_types / city — с `post`.
5. **Уведомление** (`userbot/client.py:_format_notification`):
   - Одна агрегированная карточка на пост, дедуп `(user_id, message_id)`.
   - Внутри — список подошедших вакансий.
   - В `notifications.matched_vacancy_ids` пишем id попавших вакансий.

Пример уведомления:

```
🎬 Подходящий кастинг
Тип проекта: Сериал | Город: Москва
Подходящие роли (2):
• Мама — 35–45, ж, 8000 ₽
• Каскадёр — 25–35, м, 12000 ₽

Сериал «Имя» — кастинг 5 ролей

Открыть сообщение
```

Если у вакансии нет `role_label`, fallback — русский label из справочника `role_types` либо первые ~50 символов `description`.

### Админка

`api/admin.py`:

- `AdminMessage` дополняется полем `vacancies: list[AdminVacancy]`.
- Запрос — `select(Message).options(selectinload(Message.vacancies))`, чтобы избежать N+1 при отрисовке списка сообщений.
- Webapp: на странице сообщения показываем список вакансий с их полями.

### Миграция

Новая alembic-ревизия `0007_vacancies.py`:

1. `op.create_table('vacancies', ...)` со схемой выше + индекс на `message_id` + unique `(message_id, idx)`.
2. `op.add_column('notifications', sa.Column('matched_vacancy_ids', ARRAY(Integer), nullable=True))`.
3. **Бэкфилл** (одним SQL прямо в миграции):
   ```sql
   INSERT INTO vacancies (message_id, idx, role_types, gender, age_min, age_max, rate, description, role_label)
   SELECT
     m.id,
     0,
     COALESCE(m.role_types, '{}'),
     m.gender,
     m.age_min,
     m.age_max,
     m.rate,
     m.summary,    -- per-vacancy текста для исторических строк нет, берём общий summary
     NULL
   FROM messages m
   WHERE m.is_casting = true;
   ```
4. **Downgrade**: `op.drop_table('vacancies')` + удаление колонки. Бэкфилл при downgrade не восстанавливаем (исходные данные остаются в `messages`).

**В этой миграции НЕ делаем:**

- Не удаляем legacy-колонки `messages.gender / age_min / age_max / role_types / rate` — нужны для безопасного rollback кода.
- Не трогаем `messages.age` и `messages.category` — отдельная задача.
- Не перепрогоняем исторические сообщения через новый LLM-промпт (дорого, недетерминировано).

### Порядок выкатки

1. **Миграция** деплоится на старом коде — она самодостаточна, ничего не ломает.
2. **Новый код** деплоится после — `insert_message_with_vacancies`, новый промпт, новый `matches`, новый `_format_notification`, обновлённая админка.

Это безопасно: бэкфилл выполнился до включения новой логики, у пользователей не появится «провала» в матчинге для старых постов.

## Граничные случаи и обработка ошибок

- **LLM вернул `is_casting=true` и пустой `vacancies`** — в `LLMProvider.extract()` после парсинга форсим `is_casting=false` (нет вакансий — нечего матчить). Логируем warning. Запись в `messages` всё равно пишется (для аналитики), но матчинг отбрасывает её на гейте.
- **LLM вернул дубли вакансий** (одинаковые поля) — пишем все, `idx` уникальный. Дедуп — задача LLM-промпта, не БД.
- **Дубль сообщения из Telegram** (`tg_chat_id, tg_message_id`) — `insert_message_with_vacancies` видит существующую строку и НЕ пересоздаёт вакансии. Это сохраняет id'ы, на которые уже могли быть ссылки в `notifications.matched_vacancy_ids`.
- **Пользователь подходит под 0 вакансий поста** — никаких уведомлений, как сейчас.
- **`PostExtraction` с `confidence < MIN_CONFIDENCE`** — пост игнорируется целиком, вакансии в БД не пишутся (как сейчас).
- **Бэкфилл встретил `messages.role_types = NULL`** — `COALESCE(..., '{}')` подставляет пустой массив.

## Тестирование

- **Unit:** `tests/test_matching.py` — кейсы «1 пост, 5 вакансий, профиль матчит 2/5/0», проверка возрастных диапазонов и ставок per-vacancy. Сейчас тестов нет — добавим как часть этой работы.
- **Unit LLM:** `tests/test_extract.py` — на стаб-провайдере (`llm/stub_provider.py`) проверяем парсинг JSON с `vacancies`, нормализацию кодов в каждой вакансии.
- **Integration:** в существующем стиле — пишем тестовое сообщение через `insert_message_with_vacancies`, читаем обратно, проверяем структуру.
- **Manual smoke:** деплой на staging → пост с одной ролью даёт 1 вакансию; пост с пятью даёт 5; для исторического `messages.id = 16` после миграции в `vacancies` лежит 1 строка с `idx=0` и старыми полями (это корректное поведение для legacy — re-extract не делаем).

## Out of scope

- Re-extract исторических сообщений через новый промпт.
- Удаление legacy-колонок (`messages.age`, `messages.category`, `messages.gender / age_min / age_max / role_types / rate`).
- Фича «нашлась ещё одна роль из того же поста» — задел через `matched_vacancy_ids` есть, реализация — отдельная задача.
- Раздельные карточки уведомлений (вариант А из обсуждения) — отвергнуто в пользу агрегированной.
