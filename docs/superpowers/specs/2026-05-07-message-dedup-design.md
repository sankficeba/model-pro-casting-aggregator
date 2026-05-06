# Спецификация: дедупликация форварднутых кастингов

**Дата:** 2026-05-07
**Автор:** Claude Opus 4.7
**Статус:** черновик, ожидает ревью пользователя

## Проблема

Один и тот же кастинг расходится по 30–40 каналам через нативный
Telegram-форвард или copy-paste. Каждая копия попадает в `messages` как
отдельная строка (юник `(tg_chat_id, tg_message_id)`), LLM-extract
отрабатывает 40 раз, и пользователь, чья анкета подходит под этот
кастинг, получает 40 одинаковых уведомлений.

## Цель

Свести «один кастинг = одно уведомление» в пределах разумного окна
(7 дней) при сохранении полной истории всех копий в БД для аудита.

## Не цель

- Семантическое сопоставление перефразированных кастингов (вариант C из
  brainstorm) — оставляем на запас.
- Бэкфилл исторических 187+ row’ов (они и так старше 7 дней).
- Перенотификация уже отправленных сообщений.
- Вмешательство в логику матчинга или LLM-extract.

## Решение

**Нормализованный SHA-1 хэш текста + опциональный self-FK
`canonical_message_id`.** В пределах 7-дневного окна второй прилёт
текста с тем же хэшем сохраняется в `messages` (для аудита), но
получает FK на canonical, не вызывает LLM и не порождает уведомлений.

### Нормализация

```python
def normalize(text: str) -> str:
    s = re.sub(r"^Forwarded from .*?\n", "", text, flags=re.MULTILINE)
    s = re.sub(r"https?://t\.me/\S+", "", s)
    s = re.sub(r"@[a-zA-Z0-9_]{4,}", "", s)
    s = _EMOJI_RE.sub("", s)        # U+1F300..U+1FAFF, U+2600..U+27BF
    s = re.sub(r"\s+", " ", s).strip()
    return s.casefold()

def text_hash(text: str) -> str:
    return hashlib.sha1(normalize(text).encode("utf-8")).hexdigest()
```

Точный список диапазонов эмодзи и regex для forward-header'а — в коде
`db/dedup.py`. Юнит-тесты фиксируют «два варианта одного текста дают
один хэш».

## Схема БД

Миграция `0011_message_dedup.py`:

```sql
ALTER TABLE messages
  ADD COLUMN text_hash CHAR(40) NULL,
  ADD COLUMN canonical_message_id BIGINT NULL
    REFERENCES messages(id) ON DELETE SET NULL;

CREATE INDEX ix_messages_text_hash_recent
  ON messages (text_hash, created_at DESC)
  WHERE canonical_message_id IS NULL;
```

- `text_hash` остаётся nullable: исторические row'ы не бэкфилим.
- `canonical_message_id IS NULL` ⇔ это canonical (первый прилёт).
- Partial index по `WHERE canonical_message_id IS NULL` — компактен и
  бьёт ровно в горячий путь лукапа.
- `ON DELETE SET NULL` для FK: удаление canonical не должно ронять
  child-row'ы.

## Поток обработки сообщения

```
NewMessage → text_hash(text)
              │
              ▼
        find_canonical(hash, 7d)
              │
        ┌─────┴─────┐
       YES         NO
        │           │
        ▼           ▼
  insert_duplicate_  llm.extract(text)
  message            insert_message_with_vacancies
  (FK = canonical,   (canonical row, vacancies, matching, notify)
   no vacancies,
   no LLM, return)
```

## Изменения по коду

### Новый файл `db/dedup.py`

- `normalize(text: str) -> str`
- `text_hash(text: str) -> str`

### `db/models.py`

В `Message`:
- `text_hash: Mapped[str | None] = mapped_column(String(40), nullable=True)`
- `canonical_message_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)`

### `db/repository.py`

- `find_canonical(text_hash: str, within_days: int = 7) -> Message | None`
  — `SELECT * FROM messages WHERE text_hash=? AND canonical_message_id IS NULL AND created_at > now() - 7d ORDER BY created_at LIMIT 1`.
- `insert_duplicate_message(*, tg_chat_id, tg_chat_username, tg_message_id, text, text_hash, canonical_message_id) -> int | None`
  — INSERT row с пустыми extract-полями, FK на canonical. Idempotent
  по `(tg_chat_id, tg_message_id)` (тот же `on_conflict_do_nothing`).
- `insert_message_with_vacancies(...)` — добавить параметр `text_hash`,
  кладётся в новую колонку. Сигнатура остаётся обратно-совместимой.

### `userbot/client.py`

`_handle_message`:
1. Считать `th = text_hash(text)` сразу после получения текста.
2. `canonical = await repository.find_canonical(th)`.
3. Если `canonical` не None:
   - `await repository.insert_duplicate_message(..., text_hash=th, canonical_message_id=canonical.id)`
   - `logger.info("Дубль text_hash=… canonical=…")`
   - `return`
4. Иначе — текущий путь, плюс прокидываем `text_hash=th` в
   `insert_message_with_vacancies`.

## Тесты

`tests/test_dedup.py` (новый):

1. `normalize` убирает Forward-header, t.me-ссылки, упоминания,
   эмодзи, схлопывает whitespace, casefold.
2. Два варианта одного текста (с/без header, с/без эмодзи, разные
   переносы строк) → один хэш.
3. Разные тексты → разные хэши.

`tests/test_repository.py` (расширяется):

4. `find_canonical` возвращает row внутри окна и игнорирует:
   - `canonical_message_id IS NOT NULL`
   - `created_at` старше 7 дней
   - другой `text_hash`.
5. Два `insert` подряд с одинаковым `text_hash` через userbot-флоу:
   - первый — canonical, имеет вакансии, нотификация отправлена.
   - второй — duplicate row, FK на canonical, вакансий нет,
     нотификация не создана.

## Развёртывание

1. PR → main → GitHub Actions → push образа в GHCR → `docker compose
   pull && up -d` на сервере.
2. `entrypoint.sh` запускает `alembic upgrade head` — миграция 0011
   накатывается автоматически.
3. Логи: первые часы после деплоя должны содержать строки `Дубль
   text_hash=… canonical=…` пропорционально кратности форвардов
   (ожидаем, что х30–х40 на популярные кастинги).

## Риски и митигации

| Риск | Митигация |
|---|---|
| Нормализация слишком агрессивна — два разных кастинга после strip'а сольются в один | Юнит-тесты фиксируют конкретные пары «должны разойтись». Если в проде увидим ложные срабатывания — ослабляем правила. |
| Нормализация слишком мягкая — дубли не ловятся | Логи `Дубль text_hash=…` дадут метрику «сколько процентов сообщений сейчас дедуплицируются»; если процент сильно ниже ожидаемого — пробуем варианты. |
| Канонический row LLM-extract сделал плохо (is_casting=False), а duplicate бы сделал правильно | Принимаем. Edge case, не делаем хуже статус-кво для большинства случаев. |
| Профиль пользователя обновился между canonical и duplicate (стал подходить) | Принимаем. 7-дневное окно ограничивает потерю; пользователь увидит следующий кастинг. |
| Race в окне LLM-вызова: N форвардов прилетают за <5с, все проходят `find_canonical=None` до первого commit'а canonical → каждый делает свой LLM-extract → пользователь получит N (а не 1) нотификаций. | Известно. Реалистично окно гонки = длительность LLM-call (~2-5с). В bursts на популярных кастингах (30+ форвардов) обычно только первые 5-10 успевают зайти в окно; остальные 20-25 уже видят canonical и дедуплицируются. Итого вместо 30 нотификаций ожидаем ~5-10. Если в проде окажется недостаточно — добавим UNIQUE partial index на (text_hash) WHERE canonical_message_id IS NULL + retry-as-duplicate в `insert_message_with_vacancies`. |

## Альтернативы (отклонено)

- **Bit-exact text hash** (вариант A из brainstorm): не ловит copy-paste
  с шапкой/подвалом — а это как раз классический кейс «канал
  публикует чужой пост и подписывает себя».
- **Семантический фингерпринт** (вариант C): LLM-нон-детерминизм
  ломает дедуп; плюс дорого ретроспективно. Останется в запасе на
  случай, если нормализованный hash покажет себя слишком грубым.
- **Без `canonical_message_id`, дедуп только по нотификациям**: не
  экономит LLM-токены и не убирает дубли из админки. Делаем сразу
  чище.
- **Drop duplicate row entирely**: теряем аудит «в каких каналах был
  форвард».
