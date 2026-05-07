# Message Dedup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Suppress duplicate notifications when the same casting is forwarded across many channels, by detecting near-duplicate text via a normalized SHA-1 hash within a 7-day window.

**Architecture:** New `db/dedup.py` exposes `normalize(text)` + `text_hash(text)`. `Message` model gains `text_hash` and self-FK `canonical_message_id`. Userbot computes the hash before LLM extraction; if a recent canonical row with the same hash exists, the new arrival is saved as a duplicate child row with FK on canonical and **no LLM extraction, no matching, no notification**. Old rows (text_hash NULL) naturally fall outside the 7-day lookup window — no backfill needed.

**Tech Stack:** Python 3.11, SQLAlchemy 2.0 async, Alembic, PostgreSQL, pytest + pytest-asyncio.

---

## File Structure

**Create:**
- `db/dedup.py` — `normalize(text) -> str`, `text_hash(text) -> str`. Pure functions. ~50 lines.
- `migrations/versions/0011_message_dedup.py` — Alembic migration.
- `tests/test_dedup.py` — unit tests for normalization and hashing.

**Modify:**
- `db/models.py` — add 2 fields on `Message`.
- `db/repository.py` — add `find_canonical`, `insert_duplicate_message`; thread `text_hash` through `insert_message_with_vacancies`.
- `userbot/client.py` — branch in `_handle_message` between canonical and duplicate paths.

**No DB-integration tests:** existing test suite is pure-logic (`tests/conftest.py:1-2` explicitly: «БД тут НЕ инициализируем»). The new repository functions will be exercised at deploy time against the real Postgres via the userbot. Unit tests cover the only non-trivial logic — the normalization.

---

## Task 1: `db/dedup.py` — normalize + text_hash

**Files:**
- Create: `db/dedup.py`
- Test: `tests/test_dedup.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_dedup.py` with full content:

```python
"""Тесты dedup.normalize и dedup.text_hash."""
from __future__ import annotations

from db.dedup import normalize, text_hash


def test_normalize_strips_forward_header():
    raw = "Forwarded from Кастинг канал\nИщем актёра"
    assert "forwarded from" not in normalize(raw)
    assert "ищем актёра" in normalize(raw)


def test_normalize_strips_tme_links():
    raw = "Ищем актёра https://t.me/some_channel/123 на главную роль"
    out = normalize(raw)
    assert "t.me" not in out
    assert "ищем актёра" in out
    assert "на главную роль" in out


def test_normalize_strips_mentions():
    raw = "Подавайтесь @castingdir и подписывайтесь @kasting_oca"
    out = normalize(raw)
    assert "@castingdir" not in out
    assert "@kasting_oca" not in out
    assert "подавайтесь" in out
    assert "подписывайтесь" in out


def test_normalize_strips_emoji():
    raw = "🎬 Срочно! 🔥 Ищем актёра ✨"
    out = normalize(raw)
    assert "🎬" not in out
    assert "🔥" not in out
    assert "ищем актёра" in out


def test_normalize_collapses_whitespace():
    raw = "Ищем\n\n\nактёра  на     роль"
    out = normalize(raw)
    assert out == "ищем актёра на роль"


def test_normalize_casefolds_cyrillic():
    raw = "ИЩЕМ АКТЁРА"
    out = normalize(raw)
    assert out == "ищем актёра"


def test_text_hash_is_40_char_hex():
    h = text_hash("any text")
    assert len(h) == 40
    assert all(c in "0123456789abcdef" for c in h)


def test_text_hash_same_for_normalized_equivalents():
    """Главный тест: два варианта одного текста → один хэш."""
    canonical = "Ищем актёра на главную роль в фильм"
    forwarded = (
        "Forwarded from @some_casting_channel\n\n"
        "🎬 Срочно! 🔥\n\n"
        "Ищем АКТЁРА на главную роль в фильм\n\n"
        "Подавайтесь: @castingdir\n"
        "https://t.me/some_casting_channel/123"
    )
    assert text_hash(canonical) == text_hash(forwarded)


def test_text_hash_differs_for_different_texts():
    a = "Ищем актёра на главную роль"
    b = "Ищем актрису на эпизод"
    assert text_hash(a) != text_hash(b)


def test_text_hash_handles_empty():
    """Пустой/whitespace-only текст не должен падать."""
    assert text_hash("") == text_hash("   \n\n  ")
```

- [ ] **Step 2: Run the tests to verify they fail**

```
python -m pytest tests/test_dedup.py -v
```

Expected: all FAIL with `ModuleNotFoundError: No module named 'db.dedup'`.

- [ ] **Step 3: Implement `db/dedup.py`**

Create `db/dedup.py` with full content:

```python
"""Дедуп идентичных кастингов: нормализация текста + SHA-1.

Один и тот же пост, форварднутый в десятки каналов, должен давать
один хэш. Поэтому мы аккуратно убираем «чром» канала (forward-header,
эмодзи, t.me-ссылки, упоминания) и схлопываем whitespace перед
хэшированием.
"""
from __future__ import annotations

import hashlib
import re

# Forward-header в начале строки или после переноса. Telegram ставит
# его как «Forwarded from <name>\n».
_FORWARD_RE = re.compile(r"^Forwarded from .*?$", re.MULTILINE | re.IGNORECASE)

# Ссылки на t.me — частая «реклама себя» в подвале/шапке.
_TME_RE = re.compile(r"https?://t\.me/\S+", re.IGNORECASE)

# @username — упоминания администраторов/каналов. >=4 символа, чтобы
# не ломать обычные тексты с «@» (хотя редкость в нашем домене).
_MENTION_RE = re.compile(r"@[a-zA-Z0-9_]{4,}")

# Эмодзи. Покрываем основные диапазоны Unicode emoji + dingbats.
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F9FF"  # Misc symbols + emoticons + transport + sup symbols
    "\U0001FA00-\U0001FAFF"  # Symbols and pictographs extended-A
    "\U00002600-\U000027BF"  # Dingbats + misc symbols
    "\U0001F000-\U0001F02F"  # Mahjong/dominoes
    "\U0001F0A0-\U0001F0FF"  # Playing cards
    "‍"                 # Zero-width joiner (для составных эмодзи)
    "]+",
    flags=re.UNICODE,
)

_WHITESPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Канонизирует текст для дедупа: убирает Telegram-чром,
    эмодзи, упоминания, t.me-ссылки; схлопывает whitespace; casefold."""
    s = _FORWARD_RE.sub("", text)
    s = _TME_RE.sub("", s)
    s = _MENTION_RE.sub("", s)
    s = _EMOJI_RE.sub("", s)
    s = _WHITESPACE_RE.sub(" ", s).strip()
    return s.casefold()


def text_hash(text: str) -> str:
    """SHA-1 (hex) от нормализованного текста — стабильный fingerprint
    для дедупа форварднутых постов."""
    return hashlib.sha1(normalize(text).encode("utf-8")).hexdigest()
```

- [ ] **Step 4: Run the tests to verify they pass**

```
python -m pytest tests/test_dedup.py -v
```

Expected: 10 PASS.

- [ ] **Step 5: Commit**

```
git add db/dedup.py tests/test_dedup.py
git commit -m "feat(db): normalize-and-hash for casting text dedup

normalize() strips Telegram forward-header, t.me links, @mentions,
emoji, then casefolds. text_hash() is SHA-1 over the normalized text.
Two forwarded copies of the same casting produce the same hash.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Migration 0011 + Message model

**Files:**
- Create: `migrations/versions/0011_message_dedup.py`
- Modify: `db/models.py:191-235` (Message class)

- [ ] **Step 1: Write the migration**

Create `migrations/versions/0011_message_dedup.py` with full content:

```python
"""messages: text_hash + canonical_message_id for forward-dedup

Revision ID: 0011_message_dedup
Revises: 0010_channels_tg_chat_id
Create Date: 2026-05-07

Один и тот же кастинг расходится по 30+ каналам через форвард или
copy-paste. Чтобы не спамить пользователя одним и тем же объявлением:

- text_hash: SHA-1 от нормализованного текста (см. db/dedup.py).
- canonical_message_id: self-FK на первый row с этим хэшем. У canonical
  (= оригинальной публикации) — NULL.

Бэкфилл не делаем: исторические row'ы старше 7-дневного окна, в
лукап не попадают. Новые сообщения получат hash сразу.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0011_message_dedup"
down_revision: Union[str, None] = "0010_channels_tg_chat_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("text_hash", sa.CHAR(40), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("canonical_message_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_messages_canonical",
        source_table="messages",
        referent_table="messages",
        local_cols=["canonical_message_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )
    # Partial index по горячему пути — лукап canonical-row'ов в окне.
    op.execute(
        "CREATE INDEX ix_messages_text_hash_recent "
        "ON messages (text_hash, received_at DESC) "
        "WHERE canonical_message_id IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_messages_text_hash_recent")
    op.drop_constraint("fk_messages_canonical", "messages", type_="foreignkey")
    op.drop_column("messages", "canonical_message_id")
    op.drop_column("messages", "text_hash")
```

- [ ] **Step 2: Update `db/models.py` — Message class**

Find this block in `db/models.py` (lines ~190-235):

```python
class Message(Base):
    """История сообщений из каналов с извлечёнными LLM полями."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tg_chat_username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tg_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
```

Add right after the `text` field:

```python
    # Дедуп форварднутых копий. text_hash — SHA-1 от нормализованного
    # текста (db/dedup.py). canonical_message_id указывает на первый
    # row с тем же хэшем; у canonical = NULL.
    text_hash: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    canonical_message_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )
```

If `ForeignKey` is not yet imported at the top of `db/models.py`, add it to the existing `from sqlalchemy import ...` line.

- [ ] **Step 3: Verify alembic config can see the migration**

```
python -m alembic heads
```

Expected output includes `0011_message_dedup`.

- [ ] **Step 4: Commit**

```
git add migrations/versions/0011_message_dedup.py db/models.py
git commit -m "feat(db): add text_hash + canonical_message_id to messages

Schema-only change. Migration 0011 adds two nullable columns + a partial
index over (text_hash, received_at) WHERE canonical_message_id IS NULL.
Self-FK with ON DELETE SET NULL so deleting a canonical doesn't break
its child rows. No backfill — historical messages fall outside the
7-day dedup window naturally.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Repository — find_canonical + insert_duplicate_message

**Files:**
- Modify: `db/repository.py:103-195` (MESSAGES section)

- [ ] **Step 1: Add `find_canonical`**

Insert this function in `db/repository.py` right after the `# ---------- MESSAGES ----------` comment (line 103), before `insert_message_with_vacancies`:

```python
async def find_canonical(
    text_hash: str, within_days: int = 7
) -> Optional[Message]:
    """Найти canonical-row с таким же `text_hash` внутри окна.

    Canonical — это row, у которого `canonical_message_id IS NULL`
    (он сам и есть оригинал, не дубликат). Окно отсекает старые
    реальные перепосты («второй заход на роль» через месяц считается
    новым кастингом).

    Возвращает первый найденный (минимальный id) или None.
    """
    if not text_hash:
        return None
    cutoff = datetime.now(timezone.utc) - timedelta(days=within_days)
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Message)
            .where(
                Message.text_hash == text_hash,
                Message.canonical_message_id.is_(None),
                Message.received_at > cutoff,
            )
            .order_by(Message.id.asc())
            .limit(1)
        )
        return res.scalar_one_or_none()
```

If the imports `from datetime import datetime, timezone, timedelta` are not yet present at the top of `db/repository.py`, add them to the existing datetime import line.

- [ ] **Step 2: Add `insert_duplicate_message`**

Insert this function in `db/repository.py` right after `find_canonical`:

```python
async def insert_duplicate_message(
    *,
    tg_chat_id: int,
    tg_chat_username: str | None,
    tg_message_id: int,
    text: str,
    text_hash: str,
    canonical_message_id: int,
) -> Optional[int]:
    """Записать повторное появление того же кастинга в другом канале.

    Сохраняем raw text «как пришло» (для аудита), линкуем на canonical,
    LLM-поля оставляем дефолтными (не вызываем экстрактор).
    Idempotent по (tg_chat_id, tg_message_id) через ON CONFLICT.
    """
    async with AsyncSessionLocal() as session:
        stmt = (
            pg_insert(Message)
            .values(
                tg_chat_id=tg_chat_id,
                tg_chat_username=tg_chat_username,
                tg_message_id=tg_message_id,
                text=text,
                text_hash=text_hash,
                canonical_message_id=canonical_message_id,
                # is_casting и прочие LLM-поля — дефолт (не извлекали)
            )
            .on_conflict_do_nothing(index_elements=["tg_chat_id", "tg_message_id"])
            .returning(Message.id)
        )
        res = await session.execute(stmt)
        message_id = res.scalar_one_or_none()
        await session.commit()
        return message_id
```

- [ ] **Step 3: Thread `text_hash` through `insert_message_with_vacancies`**

In `db/repository.py`, modify the function signature and body. Find:

```python
async def insert_message_with_vacancies(
    *,
    tg_chat_id: int,
    tg_chat_username: str | None,
    tg_message_id: int,
    text: str,
    extracted: PostExtraction,
) -> tuple[Optional[int], list[int]]:
```

Change to:

```python
async def insert_message_with_vacancies(
    *,
    tg_chat_id: int,
    tg_chat_username: str | None,
    tg_message_id: int,
    text: str,
    text_hash: str | None,
    extracted: PostExtraction,
) -> tuple[Optional[int], list[int]]:
```

Then in the `pg_insert(Message).values(...)` block (around line 121-132), add `text_hash=text_hash,` to the values dict — put it right after `text=text,`:

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
            )
            .on_conflict_do_nothing(index_elements=["tg_chat_id", "tg_message_id"])
            .returning(Message.id)
        )
```

- [ ] **Step 4: Sanity-check imports compile**

```
python -c "from db import repository; print('ok')"
```

Expected: `ok`. (Will fail if Message model or imports are broken.)

- [ ] **Step 5: Commit**

```
git add db/repository.py
git commit -m "feat(db): repo helpers for canonical lookup and duplicate insert

- find_canonical(text_hash, within_days=7): returns the first message
  with matching hash inside the window, where canonical_message_id IS NULL.
- insert_duplicate_message(...): writes a child row with FK on canonical,
  no LLM-extracted fields, idempotent on (chat_id, msg_id).
- insert_message_with_vacancies now accepts text_hash and stores it on
  the canonical row.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Userbot — wire dedup into `_handle_message`

**Files:**
- Modify: `userbot/client.py:176-205` (`_handle_message` method)

- [ ] **Step 1: Add the dedup import**

In `userbot/client.py`, find the existing imports (around lines 1-23). Add to the existing `from db import matching, repository` line:

```python
from db import matching, repository
from db.dedup import text_hash
```

- [ ] **Step 2: Branch on canonical lookup in `_handle_message`**

Find the current body of `_handle_message` (starts around line 176):

```python
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
```

Replace with:

```python
    async def _handle_message(self, event):
        text = (event.message.message or "").strip()
        if not text:
            return
        logger.debug("Новое сообщение: {!r}", text[:120])

        chat = event.message.chat
        chat_id = getattr(chat, "id", 0)
        chat_username = getattr(chat, "username", None)

        # Дедуп: если такой же текст (после нормализации) уже был у нас
        # за последние 7 дней — это форвард/копия. Пишем «теневой» row
        # с FK на canonical, LLM не дёргаем, нотификации не шлём.
        th = text_hash(text)
        canonical = await repository.find_canonical(th)
        if canonical is not None:
            await repository.insert_duplicate_message(
                tg_chat_id=chat_id,
                tg_chat_username=chat_username,
                tg_message_id=event.message.id,
                text=text,
                text_hash=th,
                canonical_message_id=canonical.id,
            )
            logger.info(
                "Дубль: chat={} msg={} text_hash={} canonical={}",
                chat_username or chat_id, event.message.id, th, canonical.id,
            )
            return

        post = await self.llm.extract(text)
        logger.info(
            "LLM extract: casting={} project={} city={} vacancies={} conf={:.2f}",
            post.is_casting, post.project_types, post.city,
            len(post.vacancies), post.confidence,
        )

        message_db_id, vacancy_ids = await repository.insert_message_with_vacancies(
            tg_chat_id=chat_id,
            tg_chat_username=chat_username,
            tg_message_id=event.message.id,
            text=text,
            text_hash=th,
            extracted=post,
        )
        if message_db_id is None:
            return
```

The rest of the method (matching loop, notifications) stays untouched.

- [ ] **Step 3: Run the full test suite to ensure nothing regressed**

```
python -m pytest -v
```

Expected: all existing tests + 10 new dedup tests = PASS. No regressions.

- [ ] **Step 4: Sanity-check userbot imports compile**

```
python -c "from userbot.client import Userbot; print('ok')"
```

Expected: `ok`.

- [ ] **Step 5: Commit**

```
git add userbot/client.py
git commit -m "feat(userbot): dedup forwarded casting copies via text_hash

In _handle_message, compute SHA-1 of normalized text before LLM. If a
canonical row with the same hash exists within 7 days, persist the new
arrival as a duplicate child (raw text + FK on canonical), log it, and
return — skipping LLM extract, matching, and notifications.

Fixes the case where one casting forwarded across 30+ channels resulted
in the user receiving 30+ identical notifications.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review Notes

- ✅ All four spec sections (нормализация, схема, поток, тесты) covered by tasks.
- ✅ `received_at` (not `created_at`) is the correct timestamp column on `Message` — used consistently in migration index and `find_canonical` query.
- ✅ Function names match across tasks: `normalize`, `text_hash`, `find_canonical`, `insert_duplicate_message`.
- ✅ `text_hash` parameter signature consistent (`str | None`) in repository, `str` in userbot (we always compute it before passing).
- ✅ No DB-integration tests planned — explicitly noted with the rationale (existing test suite is pure-logic).
- ✅ Migration sets index on `(text_hash, received_at DESC)` — matches the `find_canonical` ORDER BY (id asc, but column-store wise the index hits the WHERE clause; ORDER BY id is small post-filter).

---

## Deployment

After all 4 commits land on `main`:

1. GitHub Actions will build, push the image to GHCR, SSH to the server, run `docker compose pull && up -d`.
2. `entrypoint.sh` runs `alembic upgrade head` — migration 0011 applies the schema change.
3. Watch userbot logs for `Дубль: chat=… text_hash=…` lines on the next casting wave. Volume should match forward fan-out.
