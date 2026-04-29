"""Репозиторий — высокоуровневые операции над моделями.
Используется userbot'ом и aiogram-ботом."""
from __future__ import annotations

from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError

from db.models import Channel, Filter, Message, Notification, User
from db.session import AsyncSessionLocal
from models.schemas import ExtractedData, UserFilter


# ---------- USERS ----------

async def upsert_user(user_id: int, username: str | None = None) -> None:
    """Создать или обновить запись о пользователе (last_active = NOW())."""
    async with AsyncSessionLocal() as session:
        stmt = pg_insert(User).values(id=user_id, username=username)
        stmt = stmt.on_conflict_do_update(
            index_elements=[User.id],
            set_={"username": username, "last_active": stmt.excluded.last_active},
        )
        await session.execute(stmt)
        await session.commit()


# ---------- FILTERS ----------

async def upsert_single_filter(f: UserFilter) -> int:
    """Заменяет ВСЕ фильтры пользователя одним. (Совместимость с MVP-API.)
    Возвращает id новой записи."""
    async with AsyncSessionLocal() as session:
        await upsert_user_in_session(session, f.user_id)
        # Удалить все старые фильтры пользователя
        existing = await session.execute(select(Filter).where(Filter.user_id == f.user_id))
        for row in existing.scalars().all():
            await session.delete(row)
        new_filter = Filter(
            user_id=f.user_id,
            target_gender=f.target_gender,
            min_age=f.min_age,
            max_age=f.max_age,
            category=f.category,
            min_confidence=f.min_confidence,
        )
        session.add(new_filter)
        await session.commit()
        await session.refresh(new_filter)
        return new_filter.id


async def upsert_user_in_session(session, user_id: int) -> None:
    """Helper: создать пользователя в рамках уже открытой сессии."""
    stmt = pg_insert(User).values(id=user_id)
    stmt = stmt.on_conflict_do_nothing(index_elements=[User.id])
    await session.execute(stmt)


async def remove_filters(user_id: int) -> int:
    """Удалить все фильтры пользователя. Возвращает число удалённых строк."""
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(Filter).where(Filter.user_id == user_id))
        rows = existing.scalars().all()
        for row in rows:
            await session.delete(row)
        await session.commit()
        return len(rows)


async def get_user_filter(user_id: int) -> Optional[UserFilter]:
    """Вернуть первый (по id) фильтр пользователя — для совместимости с MVP-API."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Filter).where(Filter.user_id == user_id).order_by(Filter.id).limit(1)
        )
        row = res.scalar_one_or_none()
        if not row:
            return None
        return _filter_to_schema(row)


async def all_filters() -> list[UserFilter]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Filter))
        return [_filter_to_schema(r) for r in res.scalars().all()]


def _filter_to_schema(row: Filter) -> UserFilter:
    return UserFilter(
        user_id=row.user_id,
        target_gender=row.target_gender,  # type: ignore[arg-type]
        min_age=row.min_age,
        max_age=row.max_age,
        category=row.category,
        min_confidence=row.min_confidence,
    )


# ---------- MESSAGES ----------

async def insert_message(
    *,
    tg_chat_id: int,
    tg_chat_username: str | None,
    tg_message_id: int,
    text: str,
    extracted: ExtractedData,
) -> Optional[int]:
    """Вставить сообщение. Если такое уже было (chat_id, msg_id) — вернуть его id.
    Возвращает id строки в таблице messages, либо None при ошибке."""
    async with AsyncSessionLocal() as session:
        stmt = (
            pg_insert(Message)
            .values(
                tg_chat_id=tg_chat_id,
                tg_chat_username=tg_chat_username,
                tg_message_id=tg_message_id,
                text=text,
                is_casting=extracted.is_casting,
                gender=extracted.gender,
                age_min=extracted.age_min,
                age_max=extracted.age_max,
                project_types=list(extracted.project_types),
                role_types=list(extracted.role_types),
                city=extracted.city,
                rate=extracted.rate,
                summary=extracted.summary,
                confidence=extracted.confidence,
            )
            .on_conflict_do_nothing(index_elements=["tg_chat_id", "tg_message_id"])
            .returning(Message.id)
        )
        try:
            res = await session.execute(stmt)
            await session.commit()
            inserted_id = res.scalar_one_or_none()
            if inserted_id is not None:
                return inserted_id
            # Был дубль — достаём существующий id
            existing = await session.execute(
                select(Message.id).where(
                    Message.tg_chat_id == tg_chat_id,
                    Message.tg_message_id == tg_message_id,
                )
            )
            return existing.scalar_one_or_none()
        except Exception as e:  # noqa: BLE001
            logger.exception("insert_message failed: {}", e)
            await session.rollback()
            return None


# ---------- NOTIFICATIONS ----------

async def log_notification(
    *,
    user_id: int,
    message_id: int,
    success: bool,
    error: str | None = None,
    filter_id: int | None = None,
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
                )
            )
            await session.commit()
            return True
        except IntegrityError:
            await session.rollback()
            return False


# ---------- CHANNELS ----------


def _normalize_username(raw: str) -> str:
    """@MyChannel / https://t.me/MyChannel -> mychannel."""
    raw = raw.strip()
    if raw.startswith("https://t.me/"):
        raw = raw[len("https://t.me/"):]
    elif raw.startswith("t.me/"):
        raw = raw[len("t.me/"):]
    return raw.lstrip("@").strip("/").lower()


async def list_channels(active_only: bool = True) -> list[Channel]:
    async with AsyncSessionLocal() as session:
        stmt = select(Channel).order_by(Channel.id)
        if active_only:
            stmt = stmt.where(Channel.active.is_(True))
        res = await session.execute(stmt)
        return list(res.scalars().all())


async def add_channel(username: str, added_by: int) -> Optional[Channel]:
    """Добавить канал. Если уже существует и active — None.
    Если был неактивен — реактивируем."""
    norm = _normalize_username(username)
    if not norm:
        return None
    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            select(Channel).where(Channel.username == norm)
        )
        row = existing.scalar_one_or_none()
        if row is not None:
            if row.active:
                return None
            row.active = True
            row.added_by = added_by
            await session.commit()
            await session.refresh(row)
            return row
        ch = Channel(username=norm, added_by=added_by, active=True)
        session.add(ch)
        await session.commit()
        await session.refresh(ch)
        return ch


async def remove_channel(username: str) -> bool:
    """Деактивировать канал. True если действительно был активен."""
    norm = _normalize_username(username)
    if not norm:
        return False
    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            select(Channel).where(Channel.username == norm, Channel.active.is_(True))
        )
        row = existing.scalar_one_or_none()
        if row is None:
            return False
        row.active = False
        await session.commit()
        return True


async def seed_channels_if_empty(usernames: list[str], added_by: int = 0) -> int:
    """Если в БД нет каналов — заносит туда usernames из конфига.
    Возвращает количество вставленных строк."""
    if not usernames:
        return 0
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(Channel.id).limit(1))
        if existing.scalar_one_or_none() is not None:
            return 0
        added = 0
        for u in usernames:
            norm = _normalize_username(u)
            if not norm:
                continue
            session.add(Channel(username=norm, added_by=added_by, active=True))
            added += 1
        await session.commit()
        return added


# ---------- NOTIFICATIONS (продолжение) ----------


async def already_notified(user_id: int, message_id: int) -> bool:
    """Проверка, было ли уже уведомление этому пользователю по этому сообщению."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Notification.id).where(
                Notification.user_id == user_id,
                Notification.message_id == message_id,
            )
        )
        return res.scalar_one_or_none() is not None
