# Спецификация: фикс race-condition в дедупе сообщений

**Дата:** 2026-05-08
**Автор:** Claude Opus 4.7
**Статус:** черновик, ожидает ревью пользователя

## Проблема

В PR #7 (`docs/superpowers/specs/2026-05-07-message-dedup-design.md`)
задокументирована race-condition: между `find_canonical()` и
`insert_message_with_vacancies()` идёт LLM-extract длительностью
2–5 секунд. Если в это окно прилетает другой форвард того же текста,
он тоже видит `find_canonical → None` и тоже встаёт canonical-row'ом.
В результате в `messages` появляются «двойники» (например 7220 и 7224),
и пользователь получает уведомления дважды — раз за каждый canonical.

Дополнительно обнаружен второй пробел в исходном дизайне: при
`find_canonical → найден` `_handle_message` сразу возвращался, не
вызывая матчинга. Это ломало сценарий с новыми пользователями: если
юзер C зарегистрировался уже после того как canonical был обработан,
а через 1–3 дня этот же кастинг переслали в другой канал — C его
матча не получит, потому что матчинг не запускается на duplicate-row'ах.

## Цель

1. Исключить race-condition двойников на уровне эффекта для пользователя
   (даже если в `messages` иногда проскочит лишний canonical, юзер
   получит ровно одно уведомление).
2. Задним числом починить уже существующих двойников в проде.
3. Закрыть пробел с матчингом в duplicate-пути.
4. Сократить окно дедупа с 7 до 3 дней — за пределами окна перепост
   считается свежим кастингом (новые юзеры получат уведомление,
   старые — не получат благодаря per-user дедупу).

## Не цель

- Менять схему вакансий или LLM-extract.
- Хранить «процессинг-маркеры» / advisory-lock'и БД / advisory-сессии
  с многосекундным удержанием коннекта.
- Полностью гарантировать «один canonical per text_hash» на уровне
  БД. UNIQUE-индекс на messages.text_hash сломал бы legitimate
  перепост через 3+ дня.

## Решение в трёх уровнях защиты

### Уровень 1: Double-check pattern в `_handle_message`

Добавляется повторный `find_canonical(text_hash)` после LLM-extract.
Race-окно сужается с 2–5 секунд до миллисекунд между вторым SELECT'ом
и INSERT'ом.

```python
th = text_hash(text)
canonical = await repository.find_canonical(th)
if canonical is not None:
    await _process_duplicate(canonical, ...)
    return

post = await self.llm.extract(text)  # 2–5с

# Re-check: пока шёл LLM, кто-то мог закоммитить canonical
canonical = await repository.find_canonical(th)
if canonical is not None:
    await _process_duplicate(canonical, ...)
    return  # LLM-токены потеряны, но дубль не плодим

await repository.insert_message_with_vacancies(..., text_hash=th)
# матчинг + нотификации
```

### Уровень 2: Матчинг в duplicate-пути

`_process_duplicate` вместо «записал и забыл» теперь:

1. Записывает duplicate-row через `insert_duplicate_message` (как
   раньше — для аудита).
2. Грузит canonical Message + его Vacancy-rows из БД.
3. Конвертирует ORM в Pydantic-модели (`PostExtraction` +
   `list[VacancyExtraction]`).
4. Запускает `find_matching_vacancies` — список юзеров для нотификаций.
5. Для каждого матча шлёт нотификацию с `text_hash` (см. уровень 3).

Стоимость: 2 SELECT'а на duplicate-прилёт (Message + Vacancies).
LLM-токены не тратим — главная экономия дедупа сохраняется.

### Уровень 3: UNIQUE-дедуп нотификаций по text_hash

Денормализуем `text_hash` в таблицу `notifications` и добавляем
partial UNIQUE-индекс `(user_id, text_hash) WHERE text_hash IS NOT NULL`.
Дедуп в БД, без JOIN-запросов на горячем пути.

```python
async def log_notification(*, user_id, message_id, text_hash, ...) -> bool:
    async with AsyncSessionLocal() as session:
        try:
            session.add(Notification(
                user_id=user_id,
                message_id=message_id,
                text_hash=text_hash,
                ...
            ))
            await session.commit()
            return True
        except IntegrityError:
            await session.rollback()
            return False
```

Существующий `UNIQUE(user_id, message_id)` остаётся — ловит точные
повторы. Новый `UNIQUE(user_id, text_hash)` — ловит race-двойников
(разные `message_id`, одинаковый `text_hash`).

`text_hash IS NULL` для исторических notifications-записей до миграции
0011 — partial-индекс их игнорирует.

## Сужение окна дедупа: 7 → 3 дня

В `find_canonical(within_days=...)` дефолт меняется с 7 на 3.

**Аргументация:** реальные «реклама себя» перепосты идут в течение
часов–суток. После 3 дней повторный пост — это либо нерелевантный
дубль из старого архива, либо «второй заход на роль» — оба случая
лучше обработать как новый кастинг (новые юзеры получат, старые не
получат благодаря per-user дедупу в notifications).

## Сценарий новый юзер + перепост в окне

| День | Что происходит | Результат |
|---|---|---|
| 1 | Кастинг A. message 7220 → LLM → vacancies → матчинг → notification(B, 7220, H1). | B получил ✅ |
| 2 | Юзер C регистрируется, профиль матчит. | — |
| 2 | Тот же кастинг в другом канале. `find_canonical(H1, 3d)` → 7220. | Canonical найден. |
| 2 | duplicate-row 8500 (canonical=7220). LLM не вызывается. | — |
| 2 | Грузим vacancies canonical → матчинг → матчат B и C. | — |
| 2 | INSERT notification(B, 8500, H1) → UNIQUE(B, H1) → skip. | B не получил дубль ✅ |
| 2 | INSERT notification(C, 8500, H1) → INSERT успешен → Telegram. | C получил ✅ |
| 5 | Тот же кастинг репост в третий канал. `find_canonical(H1, 3d)` → None (старше 3 дней). | — |
| 5 | LLM extract → message 9000 (canonical=NULL). Свежий цикл. | — |
| 5 | Матчинг → пытается уведомить B и C. UNIQUE(B, H1) → skip; UNIQUE(C, H1) → skip. | Никто дубль не получил ✅ |

## Изменения по схеме БД

Миграция `0015_dedup_race_fix`:

```sql
-- 1. Backfill: линкуем существующих двойников на самый ранний canonical
UPDATE messages 
SET canonical_message_id = m.canonical_id 
FROM (
  SELECT text_hash, MIN(id) AS canonical_id 
  FROM messages 
  WHERE canonical_message_id IS NULL AND text_hash IS NOT NULL 
  GROUP BY text_hash
) m 
WHERE messages.text_hash = m.text_hash 
  AND messages.canonical_message_id IS NULL 
  AND messages.id != m.canonical_id;

-- 2. Денормализация: text_hash в notifications
ALTER TABLE notifications ADD COLUMN text_hash CHAR(40) NULL;

UPDATE notifications n SET text_hash = m.text_hash 
FROM messages m WHERE n.message_id = m.id AND m.text_hash IS NOT NULL;

-- 3. Удаление существующих дублей нотификаций (оставляем самую раннюю)
DELETE FROM notifications n 
USING notifications dup 
WHERE n.user_id = dup.user_id 
  AND n.text_hash = dup.text_hash 
  AND n.text_hash IS NOT NULL
  AND n.id > dup.id;

-- 4. UNIQUE partial index
CREATE UNIQUE INDEX ix_notifications_user_texthash 
ON notifications (user_id, text_hash) 
WHERE text_hash IS NOT NULL;
```

## Изменения по коду

### `db/models.py`
- `Notification`: добавить `text_hash: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)`.

### `db/repository.py`
- `find_canonical(text_hash, within_days: int = 3)` — дефолт меняется с 7 на 3.
- `log_notification(*, user_id, message_id, text_hash: str | None, ...)` — добавляется параметр; пишется в новую колонку.
- Новая функция `get_canonical_with_vacancies(canonical_id) -> tuple[Message, list[Vacancy]] | None` — грузит canonical и его vacancies одним запросом (selectinload).

### `db/matching.py`
- Helper `_orm_to_extractions(message: Message, vacancies: list[Vacancy]) -> tuple[PostExtraction, list[VacancyExtraction]]` — конвертер ORM → Pydantic.
- Опционально новая фасад-функция `find_matching_vacancies_for_canonical(canonical_id) -> dict[int, list[int]]` — обёртка вокруг `get_canonical_with_vacancies` + `find_matching_vacancies`.

### `userbot/client.py`
- `_handle_message`: рефактор. Извлечь `_process_duplicate(self, event, canonical_msg)` — общий путь и для «найден до LLM», и для «найден после LLM (race)». Добавить второй `find_canonical` после LLM-extract.
- В местах вызова `log_notification` — добавить `text_hash=th`.

## Тесты

`tests/test_repository.py` — невозможно (БД не инициализирована
для тестов в этом проекте, см. `conftest.py`).

Smoke-test через прод-логи после деплоя:

- Появление строк `Race-loser dedup: ...` подтверждает что double-check
  ловит race в реальной нагрузке.
- Появление строк `Дубль ... canonical=...` (как сейчас) при
  «нормальном» дедупе — без изменений.
- Юзеры на популярных кастингах перестают получать дубли уведомлений
  (мониторим жалобы / `notifications` table инспекция).

## Риски

| Риск | Митигация |
|---|---|
| Backfill миграции на больших таблицах | Сейчас messages ~7000 строк, notifications ~200. UPDATE с GROUP BY <1с. Принимаем. |
| Удаление дублей в notifications потеряет аудит «по какому именно сообщении уведомление шло» | Сохраняем самый ранний row (он matched original event). Поздние удаляем — это race-артефакты. Аудит по message_id остаётся через первое уведомление. |
| Сужение окна 7→3 дня снизит дедуп-рейт | Логи дадут метрику. Если в проде дубли валятся через 3-7 дней — вернём 7. Гипотеза: реальный «спам того же» — в течение 24 часов. |
| canonical_id найден, но за это время был `DELETE`'нут (например ручной cleanup) | `get_canonical_with_vacancies` возвращает None → `_process_duplicate` логирует warning и выходит. Сообщение не процессится. Принимаем — таких удалений в проде нет. |
| `find_matching_vacancies` на canonical-вакансиях с устаревшей `min_confidence` или `is_casting=False` | Гейтинг по confidence/is_casting в матчинге уже работает per-row. Если canonical был с `is_casting=False` — никого матчить не будем (как и при первом проходе). Принимаем. |
| Двойник всё-таки проскочит миллисекундное окно | UNIQUE по `(user_id, text_hash)` ловит на нотификации. Юзер не страдает. БД-аудит: возможен один-на-X лишний canonical, не критично. |

## Альтернативы (отклонено)

- **UNIQUE partial index `(text_hash) WHERE canonical_message_id IS NULL`**:
  ломает legitimate перепост через 3+ дней (новые юзеры не получат
  уведомление). Без cron-job'а / TTL-колонки нерабочий вариант.
- **Advisory lock на text_hash в БД**: 2-5 секунд держим коннект,
  риск исчерпать пул на популярных кастингах.
- **SERIALIZABLE isolation level**: тяжёлый retry-цикл, риск
  распространения serialization conflicts по системе.
- **JOIN-запрос `already_notified_by_text_hash` перед каждой
  нотификацией**: лишний SELECT на горячем пути. Денормализация
  избегает запроса целиком.
- **Notification cleanup cron-job**: отложенный фикс, окно с дублями
  всё равно открыто. UNIQUE-инвариант проще.
