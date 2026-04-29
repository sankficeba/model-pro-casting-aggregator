"""Репозиторий — высокоуровневые операции над моделями.
Используется userbot'ом и aiogram-ботом."""
from __future__ import annotations

from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError

from db.models import Channel, Filter, Message, Notification, User, Vacancy
from db.session import AsyncSessionLocal
from models.schemas import PostExtraction, UserFilter


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
                            ethnicity=list(v.ethnicity),
                            height_min=v.height_min,
                            height_max=v.height_max,
                            body_type=list(v.body_type),
                            hair_color=list(v.hair_color),
                            hair_length=list(v.hair_length),
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


# ---------- NOTIFICATIONS ----------

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


# ---------- CHANNELS ----------


def _normalize_username(raw: str) -> str:
    """@MyChannel / https://t.me/MyChannel -> mychannel."""
    raw = raw.strip()
    if raw.startswith("https://t.me/"):
        raw = raw[len("https://t.me/"):]
    elif raw.startswith("t.me/"):
        raw = raw[len("t.me/"):]
    return raw.lstrip("@").strip("/").lower()


def _parse_channel_ref(raw: str) -> tuple[str | None, int | None]:
    """Возвращает (username, tg_chat_id). Ровно одно поле не None.

    - `@my_channel` / `https://t.me/my_channel` → (`my_channel`, None)
    - `https://t.me/c/<id>[/<msg_id>]` → (None, -100<id>) — приватный канал.
    - Невалидный ввод → (None, None).
    """
    raw = raw.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
            break
    raw = raw.strip("/")
    if raw.startswith("c/"):
        chat_part = raw[2:].split("/", 1)[0]
        if chat_part.isdigit():
            # t.me/c/<id> — Telethon ожидает -100<id> для каналов/супергрупп.
            return None, int(f"-100{chat_part}")
        return None, None
    norm = raw.lstrip("@").lower()
    if not norm:
        return None, None
    return norm, None


async def list_channels(active_only: bool = True) -> list[Channel]:
    async with AsyncSessionLocal() as session:
        stmt = select(Channel).order_by(Channel.id)
        if active_only:
            stmt = stmt.where(Channel.active.is_(True))
        res = await session.execute(stmt)
        return list(res.scalars().all())


async def add_channel(ref: str, added_by: int) -> Optional[Channel]:
    """Добавить канал по @username или по приватной ссылке t.me/c/<id>.

    Если уже существует и active — None. Если был неактивен — реактивируем.
    """
    username, tg_chat_id = _parse_channel_ref(ref)
    if username is None and tg_chat_id is None:
        return None
    async with AsyncSessionLocal() as session:
        if username is not None:
            existing = await session.execute(
                select(Channel).where(Channel.username == username)
            )
        else:
            existing = await session.execute(
                select(Channel).where(Channel.tg_chat_id == tg_chat_id)
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
        ch = Channel(
            username=username,
            tg_chat_id=tg_chat_id,
            added_by=added_by,
            active=True,
        )
        session.add(ch)
        await session.commit()
        await session.refresh(ch)
        return ch


async def remove_channel(ref: str) -> bool:
    """Деактивировать канал. True если действительно был активен."""
    username, tg_chat_id = _parse_channel_ref(ref)
    if username is None and tg_chat_id is None:
        return False
    async with AsyncSessionLocal() as session:
        if username is not None:
            stmt = select(Channel).where(
                Channel.username == username, Channel.active.is_(True)
            )
        else:
            stmt = select(Channel).where(
                Channel.tg_chat_id == tg_chat_id, Channel.active.is_(True)
            )
        existing = await session.execute(stmt)
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
