# Dedup Race-Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Закрыть race condition в дедупе сообщений за счёт сужения окна гонки (double-check), матчинга в duplicate-пути и БД-инварианта `(user_id, text_hash)` в notifications. Сократить окно дедупа с 7 до 3 дней.

**Architecture:** 3 уровня защиты — (1) повторный `find_canonical` после LLM-extract сужает окно с 2-5с до миллисекунд; (2) duplicate-путь больше не возвращается рано — грузит canonical-вакансии и матчит; (3) UNIQUE partial index `(user_id, text_hash)` в notifications делает дедуп нотификаций инвариантом БД, без JOIN на горячем пути.

**Tech Stack:** SQLAlchemy 2.0 async + Alembic, FastAPI, Telethon userbot, aiogram bot, pytest.

**Spec:** `docs/superpowers/specs/2026-05-08-dedup-race-fix-design.md`.

---

## Task 1: Миграция 0015 + Notification.text_hash

**Files:**
- Create: `migrations/versions/0015_dedup_race_fix.py`
- Modify: `db/models.py` (добавить `text_hash` в `Notification`)

- [ ] **Step 1: Написать миграцию 0015**

Создать `D:\Documents\Claude\Projects\model_pro\migrations\versions\0015_dedup_race_fix.py`:

```python
"""dedup race fix: backfill canonical + notifications text_hash + UNIQUE

Revision ID: 0015_dedup_race_fix
Revises: 0014_experience_text
Create Date: 2026-05-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0015_dedup_race_fix"
down_revision: Union[str, None] = "0014_experience_text"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Backfill: связать существующих двойников в messages с самым ранним
    #    canonical-row'ом с тем же text_hash.
    op.execute(
        """
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
        """
    )

    # 2. Денормализация: text_hash в notifications
    op.add_column(
        "notifications",
        sa.Column("text_hash", sa.String(40), nullable=True),
    )

    # 3. Backfill text_hash из messages
    op.execute(
        """
        UPDATE notifications n
        SET text_hash = m.text_hash
        FROM messages m
        WHERE n.message_id = m.id AND m.text_hash IS NOT NULL;
        """
    )

    # 4. Удалить существующие дубли нотификаций (оставляем самую раннюю
    #    по id; UNIQUE-индекс ниже не накатился бы при их наличии).
    op.execute(
        """
        DELETE FROM notifications n
        USING notifications dup
        WHERE n.user_id = dup.user_id
          AND n.text_hash = dup.text_hash
          AND n.text_hash IS NOT NULL
          AND n.id > dup.id;
        """
    )

    # 5. Partial UNIQUE-индекс: один user × один text_hash = одно уведомление.
    #    Исторические записи с text_hash IS NULL не участвуют.
    op.create_index(
        "ix_notifications_user_texthash",
        "notifications",
        ["user_id", "text_hash"],
        unique=True,
        postgresql_where=sa.text("text_hash IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_texthash", table_name="notifications")
    op.drop_column("notifications", "text_hash")
    # Backfill canonical_message_id не откатываем — это data fix, не схема.
```

- [ ] **Step 2: Скомпилировать миграцию**

```bash
python -m py_compile migrations/versions/0015_dedup_race_fix.py
```

Expected: 0 errors.

- [ ] **Step 3: Добавить `text_hash` в Notification модель**

Открыть `D:\Documents\Claude\Projects\model_pro\db\models.py`. Найти класс `Notification` (около строки 295). Добавить поле `text_hash` после поля `filter_id`:

```python
class Notification(Base):
    """Лог уведомлений: какому пользователю по какому фильтру и какому сообщению ушло."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    # Хвост от старой модели; сейчас всегда NULL (матч идёт по actor_profiles).
    filter_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Денормализация text_hash из связанного Message: позволяет UNIQUE-дедуп
    # «один text_hash → одно уведомление на юзера» без JOIN на горячем пути.
    text_hash: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    matched_vacancy_ids: Mapped[Optional[list[int]]] = mapped_column(
        ARRAY(Integer), nullable=True,
    )

    __table_args__ = (
        # Дедуп: один пользователь не получает одно и то же сообщение дважды
        UniqueConstraint("user_id", "message_id", name="uq_notifications_user_msg"),
    )
```

- [ ] **Step 4: Smoke-test модель**

```bash
python -c "from db.models import Notification; print('text_hash field:', hasattr(Notification, 'text_hash'))"
```

Expected: `text_hash field: True`.

- [ ] **Step 5: Commit**

```bash
git add migrations/versions/0015_dedup_race_fix.py db/models.py
git commit -m "$(cat <<'EOF'
feat(db): migration 0015 — dedup race fix backfill + notifications text_hash

Backfill canonical_message_id for existing twins (race-condition
artifacts), denormalize text_hash into notifications, dedupe existing
duplicate notifications, add partial UNIQUE index.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Repository — find_canonical default 3, log_notification с text_hash, get_canonical_with_vacancies

**Files:**
- Modify: `db/repository.py` (3 функции изменить, 1 добавить)

- [ ] **Step 1: Сократить окно `find_canonical` с 7 до 3 дней**

В `D:\Documents\Claude\Projects\model_pro\db\repository.py` найти функцию `find_canonical` (около строки 106). Изменить дефолт параметра с 7 на 3:

```python
async def find_canonical(
    text_hash: str, within_days: int = 3
) -> Optional[Message]:
    """Найти canonical-row с таким же `text_hash` внутри окна.
    ...
    """
```

И обновить docstring чтобы отражать новое окно (`«второй заход на роль» через 3+ дней считается новым кастингом`).

- [ ] **Step 2: Добавить параметр `text_hash` в `log_notification`**

В `db/repository.py` найти функцию `log_notification` (около строки 285). Добавить параметр `text_hash: str | None = None` и пробросить в Notification:

```python
async def log_notification(
    *,
    user_id: int,
    message_id: int,
    text_hash: str | None = None,
    success: bool,
    error: str | None = None,
    filter_id: int | None = None,
    matched_vacancy_ids: list[int] | None = None,
) -> bool:
    """Записать уведомление. Возвращает True, если запись создана,
    False если уже было (дубль) — это и есть наш дедуп.

    text_hash денормализуется из Message для UNIQUE(user_id, text_hash)
    дедупа на race-двойниках (разные message_id, одинаковый текст)."""
    async with AsyncSessionLocal() as session:
        try:
            session.add(
                Notification(
                    user_id=user_id,
                    message_id=message_id,
                    text_hash=text_hash,
                    filter_id=filter_id,
                    success=success,
                    error=error,
                    matched_vacancy_ids=matched_vacancy_ids,
                )
            )
            await session.commit()
            return True
        except IntegrityError:
            # Сработал любой UNIQUE: либо (user_id, message_id), либо
            # (user_id, text_hash). Оба означают «уже уведомили».
            await session.rollback()
            return False
```

- [ ] **Step 3: Добавить `get_canonical_with_vacancies`**

В конец секции `# ---------- MESSAGES ----------` (после `insert_message_with_vacancies`, около строки 264) добавить новую функцию:

```python
async def get_canonical_with_vacancies(
    canonical_id: int,
) -> Optional[tuple[Message, list[Vacancy]]]:
    """Загрузить canonical-row и его вакансии одним заходом.

    Используется в duplicate-пути _handle_message: когда новый прилёт
    того же текста обнаружен через find_canonical, надо запустить
    матчинг по уже-извлечённым LLM вакансиям canonical-row'а
    (без повторного LLM-extract'а).
    """
    async with AsyncSessionLocal() as session:
        msg_res = await session.execute(
            select(Message).where(Message.id == canonical_id)
        )
        msg = msg_res.scalar_one_or_none()
        if msg is None:
            return None
        vac_res = await session.execute(
            select(Vacancy)
            .where(Vacancy.message_id == canonical_id)
            .order_by(Vacancy.idx)
        )
        vacancies = list(vac_res.scalars().all())
        return msg, vacancies
```

Импорт `Vacancy` уже есть в файле (строка ~13: `from db.models import Channel, Filter, Message, Notification, User, Vacancy`).

- [ ] **Step 4: Smoke-test**

```bash
python -c "from db.repository import find_canonical, log_notification, get_canonical_with_vacancies; import inspect; sig = inspect.signature(find_canonical); print('find_canonical default:', sig.parameters['within_days'].default); sig = inspect.signature(log_notification); print('log_notification has text_hash:', 'text_hash' in sig.parameters)"
```

Expected: `find_canonical default: 3` and `log_notification has text_hash: True`.

- [ ] **Step 5: Commit**

```bash
git add db/repository.py
git commit -m "$(cat <<'EOF'
feat(db): repository — find_canonical 3d window + log_notification text_hash + get_canonical_with_vacancies

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Matching — ORM → Pydantic конвертер для duplicate-пути

**Files:**
- Modify: `db/matching.py` (добавить хелпер-функцию)
- Create: `tests/test_matching_orm_convert.py`

- [ ] **Step 1: Написать тест-конвертер (TDD)**

Создать `D:\Documents\Claude\Projects\model_pro\tests\test_matching_orm_convert.py`:

```python
"""Конвертер ORM Message + Vacancy → Pydantic PostExtraction + VacancyExtraction.

Используется в duplicate-пути _handle_message: грузим canonical из
БД и конвертируем для прогона через find_matching_vacancies."""
from datetime import datetime, timezone

from db.matching import _orm_to_extractions
from db.models import Message, Vacancy


def _make_message(**overrides) -> Message:
    msg = Message(
        id=1,
        tg_chat_id=-1001234,
        tg_chat_username="ch",
        tg_message_id=42,
        text="Test",
        text_hash="a" * 40,
        is_casting=True,
        gender="female",
        age_min=18,
        age_max=25,
        project_types=["advertising"],
        role_types=["main"],
        city="Москва",
        rate=10000,
        summary="summary",
        confidence=0.95,
        received_at=datetime.now(timezone.utc),
    )
    for k, v in overrides.items():
        setattr(msg, k, v)
    return msg


def _make_vacancy(**overrides) -> Vacancy:
    vac = Vacancy(
        id=1,
        message_id=1,
        idx=0,
        role_types=["main"],
        gender="female",
        age_min=20,
        age_max=30,
        rate=15000,
        ethnicity=["slavic"],
        height_min=160,
        height_max=180,
        body_type=["athletic"],
        hair_color=["brown"],
        hair_length=["medium"],
        description="desc",
        role_label="Главная роль",
    )
    for k, v in overrides.items():
        setattr(vac, k, v)
    return vac


def test_orm_to_extractions_post_fields():
    msg = _make_message()
    post, vacs = _orm_to_extractions(msg, [])
    assert post.is_casting is True
    assert post.project_types == ["advertising"]
    assert post.city == "Москва"
    assert post.summary == "summary"
    assert post.confidence == 0.95
    assert vacs == []


def test_orm_to_extractions_vacancy_fields():
    msg = _make_message()
    vac = _make_vacancy()
    _, vacs = _orm_to_extractions(msg, [vac])
    assert len(vacs) == 1
    v = vacs[0]
    assert v.role_types == ["main"]
    assert v.gender == "female"
    assert v.age_min == 20
    assert v.age_max == 30
    assert v.rate == 15000
    assert v.ethnicity == ["slavic"]
    assert v.height_min == 160
    assert v.height_max == 180
    assert v.body_type == ["athletic"]
    assert v.hair_color == ["brown"]
    assert v.hair_length == ["medium"]
    assert v.description == "desc"
    assert v.role_label == "Главная роль"


def test_orm_to_extractions_multiple_vacancies_preserves_order():
    msg = _make_message()
    v1 = _make_vacancy(id=1, idx=0, role_label="Первая")
    v2 = _make_vacancy(id=2, idx=1, role_label="Вторая")
    _, vacs = _orm_to_extractions(msg, [v1, v2])
    assert [v.role_label for v in vacs] == ["Первая", "Вторая"]


def test_orm_to_extractions_handles_nullable_fields():
    msg = _make_message(gender=None, age_min=None, age_max=None, rate=None, summary=None, city=None)
    vac = _make_vacancy(gender=None, age_min=None, age_max=None, rate=None, role_label=None, description=None)
    post, vacs = _orm_to_extractions(msg, [vac])
    assert post.city is None
    assert post.summary is None
    assert vacs[0].gender is None
    assert vacs[0].role_label is None
```

- [ ] **Step 2: Запустить тесты — ожидание FAIL**

```bash
pytest tests/test_matching_orm_convert.py -v
```

Expected: ImportError или AttributeError на `_orm_to_extractions`.

- [ ] **Step 3: Реализовать `_orm_to_extractions`**

В `D:\Documents\Claude\Projects\model_pro\db\matching.py`. Текущие импорты (строки 1-11) уже включают `PostExtraction`, `VacancyExtraction` и модели `ActorProfile/Message/Vacancy`. После функции `find_matching_vacancies` (около строки 124) добавить:

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
        project_types=list(message.project_types),
        city=message.city,
        summary=message.summary,
        confidence=message.confidence,
        vacancies=[],  # заполняется ниже отдельным списком
    )
    vac_extractions = [
        VacancyExtraction(
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
        )
        for v in vacancies
    ]
    return post, vac_extractions
```

- [ ] **Step 4: Запустить тесты — ожидание PASS**

```bash
pytest tests/test_matching_orm_convert.py -v
```

Expected: 4 passed.

Если в `PostExtraction` поле `vacancies` обязательное и не принимает пустой список — посмотреть `models/schemas.py`. Скорее всего конструктор примет список (по умолчанию). Если возникнет валидационная ошибка с другим полем — следовать сигнатуре `PostExtraction` из `models/schemas.py`.

- [ ] **Step 5: Commit**

```bash
git add db/matching.py tests/test_matching_orm_convert.py
git commit -m "$(cat <<'EOF'
feat(matching): _orm_to_extractions — convert ORM Message+Vacancy to Pydantic

Used by userbot duplicate-path: load canonical from DB and run
matching on already-extracted vacancies without re-invoking LLM.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: userbot — _process_duplicate, double-check, text_hash в нотификациях

**Files:**
- Modify: `userbot/client.py` (рефактор `_handle_message`, новая функция `_process_duplicate`, передача `text_hash` в `log_notification`)

- [ ] **Step 1: Прочитать текущий `_handle_message` и точки вызова `log_notification`**

Открыть `D:\Documents\Claude\Projects\model_pro\userbot\client.py`. Найти:
- `_handle_message` (около строки 177)
- Все вызовы `repository.log_notification(...)` — обычно сразу после `bot.send_message`. Найти grep'ом:

```bash
```

(Не выполнять команду — это пометка имплементеру для ориентировки. Ниже даны конкретные правки.)

- [ ] **Step 2: Извлечь общий путь обработки в helper `_process_canonical`**

В `userbot/client.py`. Сейчас `_handle_message` после успешного `insert_message_with_vacancies` запускает матчинг и шлёт нотификации. Этот же путь должен запускаться для duplicate-row'ов (с canonical-вакансиями). Извлечь общую часть в метод класса:

```python
async def _process_canonical(
    self,
    *,
    message_db_id: int,
    text_hash_value: str,
    post: "PostExtraction",
    vacancies: list["VacancyExtraction"],
    raw_text: str,
    chat_id: int,
    chat_username: str | None,
    tg_message_id: int,
) -> None:
    """Общий путь матчинга и нотификаций.

    Вызывается:
    - На свежий canonical (после успешного insert_message_with_vacancies).
    - На duplicate-прилёт (после insert_duplicate_message + загрузки
      canonical из БД через get_canonical_with_vacancies).

    text_hash_value пробрасывается в log_notification → UNIQUE
    (user_id, text_hash) гарантирует «один кастинг = одно уведомление
    на юзера за всю историю».
    """
    matches = await matching.find_matching_vacancies(post, vacancies)
    if not matches:
        return

    # Здесь идёт уже существующий код _handle_message по отправке
    # нотификаций каждому матчу. Перенести его сюда. В каждом вызове
    # repository.log_notification — добавить text_hash=text_hash_value.
    # ВАЖНО: log_notification вызывается ДО bot.send_message — так что
    # UNIQUE-конфликт мы ловим раньше отправки. Если log_notification
    # вернул False (уже было) — пропускаем send_message для этого юзера.
    ...
```

Конкретный код блока «отправка нотификаций» уже есть в `_handle_message` — переносится 1:1 с одной правкой: каждый вызов `log_notification(...)` получает дополнительный параметр `text_hash=text_hash_value`.

Если в текущем `_handle_message` логика такая (примерный псевдокод):
```python
matches = await matching.find_matching_vacancies(post, vacancies)
for user_id, vac_indices in matches.items():
    matched_vacancy_db_ids = [vacancy_ids[i] for i in vac_indices]
    if await repository.already_notified(user_id, message_db_id):
        continue
    text = self._compose_notification_text(...)
    try:
        await self.bot.send_message(...)
        await repository.log_notification(
            user_id=user_id,
            message_id=message_db_id,
            success=True,
            matched_vacancy_ids=matched_vacancy_db_ids,
        )
    except Exception as e:
        await repository.log_notification(
            user_id=user_id,
            message_id=message_db_id,
            success=False,
            error=str(e),
        )
```

…то правка такая (ИЗМЕНЕНИЯ ПОМЕЧЕНЫ КОММЕНТАРИЯМИ):

```python
matches = await matching.find_matching_vacancies(post, vacancies)
for user_id, vac_indices in matches.items():
    matched_vacancy_db_ids = [vacancy_ids[i] for i in vac_indices] if vacancy_ids else []
    # Было: if await already_notified(user_id, message_db_id): continue
    # Теперь: вместо предварительной проверки полагаемся на UNIQUE в
    # log_notification — пишем сначала, и если конфликт (False) —
    # пропускаем send_message. Это race-safe.
    text = self._compose_notification_text(...)
    log_ok = await repository.log_notification(
        user_id=user_id,
        message_id=message_db_id,
        text_hash=text_hash_value,  # NEW
        success=True,  # «оптимистично»
        matched_vacancy_ids=matched_vacancy_db_ids,
    )
    if not log_ok:
        continue  # уже уведомили (по message_id ИЛИ по text_hash)
    try:
        await self.bot.send_message(...)
    except Exception as e:
        # Update — отметить запись как failed. Простейший вариант —
        # отдельный repository.mark_notification_failed(user_id, message_id, error).
        # Если такой функции нет — оставить как success=True (не блокирует).
        logger.warning("send_message failed for {}: {}", user_id, e)
```

ЕСЛИ имплементер видит, что в текущем коде `log_notification` вызывается ПОСЛЕ `bot.send_message` (для записи success/error) — порядок важен. Нужно переключить: log_notification ПЕРЕД send_message, потому что мы используем INSERT ON CONFLICT для дедупа. Если `log_notification` вернул False — не шлём.

Если send_message упал — уведомление в БД помечено success=True, но физически не доставлено. Это потенциальный регресс, но в этом проекте текущая логика и так теряет нотификации при падениях бота, поэтому не делаем хуже. (Альтернативное решение: после неудачного send_message сделать `repository.update_notification(user_id, message_id, success=False, error=str(e))` — но новый метод. Здесь не делаем; помечаем как нюанс в self-review.)

ВАЖНО: реализовать по фактическому коду в `_handle_message` — он может отличаться от псевдокода выше. Имплементер должен:
1. Прочитать существующий `_handle_message` целиком.
2. Извлечь блок матчинга+отправки в `_process_canonical`, добавив параметры из сигнатуры выше.
3. В каждом вызове `log_notification(...)` добавить `text_hash=text_hash_value`.
4. Заменить вызов внутри `_handle_message` на `await self._process_canonical(...)`.

- [ ] **Step 3: Добавить `_process_duplicate` для дедуп-пути**

После `_process_canonical` добавить:

```python
async def _process_duplicate(
    self,
    event,  # noqa: ANN001
    canonical_msg: "Message",  # из db.models
    text_hash_value: str,
    chat_id: int,
    chat_username: str | None,
) -> None:
    """Обработать duplicate-прилёт: записать аудит-row в messages + 
    запустить матчинг на canonical-вакансиях.

    LLM-extract не дёргается (это и есть смысл дедупа), но матчинг
    нужен — новые юзеры, зарегистрированные после canonical-обработки,
    могут матчить тот же кастинг. UNIQUE(user_id, text_hash) в
    notifications не даст уже уведомлённым получить дубль.
    """
    raw_text = (event.message.message or "").strip()
    dup_id = await repository.insert_duplicate_message(
        tg_chat_id=chat_id,
        tg_chat_username=chat_username,
        tg_message_id=event.message.id,
        text=raw_text,
        text_hash=text_hash_value,
        canonical_message_id=canonical_msg.id,
    )
    logger.info(
        "Дубль: chat={} msg={} text_hash={} canonical={} dup_row={}",
        chat_id, event.message.id, text_hash_value, canonical_msg.id, dup_id,
    )

    loaded = await repository.get_canonical_with_vacancies(canonical_msg.id)
    if loaded is None:
        logger.warning(
            "Canonical {} disappeared between find and load — skipping match",
            canonical_msg.id,
        )
        return
    canon_msg, canon_vacancies = loaded
    post, vac_extractions = matching._orm_to_extractions(canon_msg, canon_vacancies)

    # Матчинг и нотификации по canonical. message_db_id для нотификаций
    # — это id duplicate-row'а (для аудита «по какому именно прилёту
    # юзеру ушло»). Если dup_id is None (race на (chat_id, msg_id)) —
    # используем canonical_msg.id.
    notify_message_id = dup_id if dup_id is not None else canonical_msg.id
    # vacancy_ids в духе оригинала — это ID Vacancy в БД (canonical's).
    canonical_vacancy_ids = [v.id for v in canon_vacancies]
    await self._process_canonical(
        message_db_id=notify_message_id,
        text_hash_value=text_hash_value,
        post=post,
        vacancies=vac_extractions,
        raw_text=raw_text,
        chat_id=chat_id,
        chat_username=chat_username,
        tg_message_id=event.message.id,
    )
```

ЕСЛИ `_process_canonical` принимает `vacancy_ids` параметром (для логгирования в `matched_vacancy_ids` нотификации) — добавить его в сигнатуру и передать `canonical_vacancy_ids`. См. Step 2.

Импорты в верх файла: добавить `from db.models import Message` (если ещё не импортирован) для type hint. Текущие импорты включают `from db import matching, repository`.

- [ ] **Step 4: Переписать `_handle_message` — double-check + использование хелперов**

Найти существующий `_handle_message` и переписать:

```python
async def _handle_message(self, event):
    text = (event.message.message or "").strip()
    if not text:
        return

    chat_id = event.chat_id
    chat = await event.get_chat()
    chat_username = getattr(chat, "username", None)

    th = text_hash(text)

    # 1. Pre-LLM check: если canonical уже есть в окне 3 дней — 
    #    duplicate-путь, без LLM.
    canonical = await repository.find_canonical(th)
    if canonical is not None:
        await self._process_duplicate(event, canonical, th, chat_id, chat_username)
        return

    # 2. LLM extract — 2-5 секунд, race-окно.
    post = await self.llm.extract(text)
    logger.info(
        "LLM extracted: is_casting={} vacancies={} confidence={}",
        post.is_casting, len(post.vacancies), post.confidence,
    )

    # 3. Re-check: пока шёл LLM, кто-то другой мог закоммитить canonical
    #    с тем же text_hash. Если так — переключаемся в duplicate-путь.
    canonical = await repository.find_canonical(th)
    if canonical is not None:
        logger.info(
            "Race-loser: canonical {} appeared during LLM extract for hash {}",
            canonical.id, th,
        )
        await self._process_duplicate(event, canonical, th, chat_id, chat_username)
        return

    # 4. Свежий canonical — пишем + матчинг + нотификации.
    message_db_id, vacancy_ids = await repository.insert_message_with_vacancies(
        tg_chat_id=chat_id,
        tg_chat_username=chat_username,
        tg_message_id=event.message.id,
        text=text,
        text_hash=th,
        extracted=post,
    )
    if message_db_id is None:
        logger.warning("insert_message_with_vacancies returned None — skipping match")
        return

    await self._process_canonical(
        message_db_id=message_db_id,
        text_hash_value=th,
        post=post,
        vacancies=post.vacancies,
        raw_text=text,
        chat_id=chat_id,
        chat_username=chat_username,
        tg_message_id=event.message.id,
    )
```

ЕСЛИ существующий `_handle_message` имеет нюансы (например, дополнительные проверки на вебхуке, фильтры по chat_id), сохранить эти проверки в начале функции, а блок «после получения text» переписать как выше.

- [ ] **Step 5: Smoke-test импорта**

```bash
python -c "from userbot.client import Userbot; print('userbot ok')"
```

Expected: `userbot ok`.

- [ ] **Step 6: Запустить весь pytest, чтобы убедиться что ничего не сломалось**

```bash
pytest tests/test_dedup.py tests/test_matching_orm_convert.py tests/test_schemas_per_category.py tests/test_suggestions.py -v
```

Expected: всё проходит.

- [ ] **Step 7: Commit**

```bash
git add userbot/client.py
git commit -m "$(cat <<'EOF'
feat(userbot): double-check + matching in duplicate-path + text_hash in notifications

- _handle_message: re-check find_canonical after LLM extract closes
  the race window from 2-5s to milliseconds.
- _process_duplicate: load canonical's vacancies and run matching —
  new users registered after canonical was processed now receive the
  notification on legitimate reposts within 3 days.
- All log_notification calls now pass text_hash, so UNIQUE
  (user_id, text_hash) in notifications dedupes race-twins at the DB
  level.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Push branch + open PR

- [ ] **Step 1: Push branch**

```bash
git push -u origin fix/dedup-race
```

- [ ] **Step 2: Create PR**

```bash
gh pr create --title "fix(dedup): race-condition fix — double-check + duplicate-path matching + UNIQUE notifications" --body "$(cat <<'EOF'
## Summary

3 уровня защиты от race condition в дедупе сообщений + сужение окна с 7 до 3 дней.

### 1. Double-check в `_handle_message`
Повторный `find_canonical` после LLM-extract сужает race-окно с 2-5с до миллисекунд между вторым SELECT'ом и INSERT'ом.

### 2. Матчинг в duplicate-пути
Закрывает реальный пробел: новые юзеры, зарегистрированные после обработки canonical, теперь получают уведомления на legitimate перепостах в окне 3 дней. Грузим `canonical` + его vacancies из БД и прогоняем `find_matching_vacancies` — без повторного LLM-extract'а.

### 3. UNIQUE `(user_id, text_hash)` в notifications
Денормализуем `text_hash` в notifications и добавляем partial UNIQUE. Дедуп нотификаций теперь — БД-инвариант, без JOIN'ов на горячем пути. Существующие дубли уведомлений и canonical-двойники подчищаются в backfill миграции 0015.

## Migrations
- `0015_dedup_race_fix` — backfill canonical_message_id для существующих двойников; добавление `notifications.text_hash` + backfill из messages; удаление существующих дублей нотификаций; partial UNIQUE.

## Test plan
- [ ] `pytest tests/test_matching_orm_convert.py` — ORM-конвертер
- [ ] После деплоя — мониторинг логов userbot:
  - Появление `Race-loser: canonical N appeared during LLM extract` подтверждает что double-check ловит race в живой нагрузке.
  - Уменьшение / исчезновение жалоб юзеров на дубли уведомлений.
- [ ] Прямой SQL-чек на проде: `SELECT text_hash, COUNT(*) FROM messages WHERE canonical_message_id IS NULL AND text_hash IS NOT NULL GROUP BY text_hash HAVING COUNT(*) > 1` — должно вернуть 0 строк сразу после деплоя (благодаря backfill).

## Спек
`docs/superpowers/specs/2026-05-08-dedup-race-fix-design.md`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: Сообщить URL PR**

После успешного `gh pr create` — gh выведет URL. Записать в отчёт.

---

## Self-review notes

**Spec coverage:**
- Уровень 1 (double-check): Task 4 Step 4.
- Уровень 2 (матчинг в dup-пути): Task 4 Step 3 (`_process_duplicate`).
- Уровень 3 (UNIQUE notifications): Task 1 миграция + Task 2 `log_notification(text_hash=...)` + Task 4 пробрасывание.
- Сужение окна 7→3: Task 2 Step 1.
- Backfill canonical: Task 1 Step 1 (миграция).
- Backfill notifications + UNIQUE: Task 1 Step 1.

**Тесты:** только для `_orm_to_extractions` (pure-функция). Остальное — БД-зависимое, без интеграционных тестов в проекте; smoke-test через прод-логи (Task 5).

**Известные нюансы:**
- Task 4 Step 2 предлагает переключить порядок `log_notification` ↔ `bot.send_message` — `log_notification` СНАЧАЛА. Если send_message падает, нотификация в БД помечена success=True, физически не доставлена. Не хуже текущего поведения проекта (там тоже теряются при падениях). Если важно — отдельный спек, добавить `update_notification_failed`.
- Task 4 строит на структуре существующего `_handle_message` без точных line numbers. Имплементер должен прочитать файл и адаптировать.
