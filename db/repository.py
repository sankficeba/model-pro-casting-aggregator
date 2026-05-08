"""Репозиторий — высокоуровневые операции над моделями.
Используется userbot'ом и aiogram-ботом."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from loguru import logger
from sqlalchemy import func as sa_func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError

from db.models import (
    ActorProfile,
    AdminProfile,
    Channel,
    CreativeProfile,
    EventProfile,
    Filter,
    GeneralProfile,
    Message,
    Notification,
    PendingNotification,
    User,
    UserCategorySubscription,
    Vacancy,
)
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

async def find_canonical(
    text_hash: str, within_days: int = 3
) -> Optional[Message]:
    """Найти canonical-row с таким же `text_hash` внутри окна.

    Canonical — это row, у которого `canonical_message_id IS NULL`
    (он сам и есть оригинал, не дубликат). Окно отсекает старые
    реальные перепосты («второй заход на роль» через 3+ дней считается
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


async def insert_message_with_vacancies(
    *,
    tg_chat_id: int,
    tg_chat_username: str | None,
    tg_message_id: int,
    text: str,
    text_hash: str | None,
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
                            category=v.category,
                            work_types=list(v.work_types),
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


async def get_vacancy_with_message(
    vacancy_id: int,
) -> Optional[tuple[Vacancy, Message]]:
    """Загрузить вакансию + её родительский Message за один заход.
    Используется хэндлером отклика — нужны обе сущности для шаблона."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Vacancy, Message)
            .join(Message, Message.id == Vacancy.message_id)
            .where(Vacancy.id == vacancy_id)
        )
        row = res.first()
        if row is None:
            return None
        return row[0], row[1]


# ---------- NOTIFICATIONS ----------

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


async def update_notification_failed(
    *, user_id: int, message_id: int, error: str
) -> None:
    """Пометить уже-вставленную нотификацию как failed после упавшего send_message.

    Используется когда мы оптимистично ставим success=True перед send_message
    (для UNIQUE-дедупа), а потом отправка упала — обновляем запись."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.message_id == message_id,
            )
            .values(success=False, error=error)
        )
        await session.commit()


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


# ====================================================================
# CATEGORIES & PER-CATEGORY PROFILES (mini-app categories feature)
# ====================================================================

CATEGORY_TO_MODEL = {
    "creative": CreativeProfile,
    "event": EventProfile,
    "general": GeneralProfile,
    "admin": AdminProfile,
}

# Канонические скалярные поля, которые шарятся между категориями
# и попадают в /api/profile/suggestions. multi-select поля и
# category-специфичные (project_types, work_types) — НЕ включаем.
_SUGGESTION_FIELDS = {
    "full_name", "gender", "city", "actual_age", "min_rate",
    "height_cm", "clothing_size", "shoe_size",
    "hair_color", "hair_length",
    "tax_status", "education", "phone", "vk_url",
    "telegram_user", "email", "portfolio_url", "video_url",
}

# Required-поля per category для расчёта completion_pct в меню Mini App.
# Должно совпадать с frontend-validate() в каждой форме (webapp/src/forms/*).
_REQUIRED_FIELDS = {
    "creative": [
        "full_name", "gender", "city", "actual_age",
        "project_types", "role_types",
        "height_cm", "ethnicity", "body_type", "hair_color", "hair_length",
        "phone", "email",
    ],
    "event": [
        "full_name", "gender", "city", "actual_age",
        "work_types", "phone", "email",
    ],
    "general": [
        "full_name", "gender", "city", "actual_age",
        "work_types", "phone", "email",
    ],
    "admin": [
        "full_name", "gender", "city", "actual_age",
        "work_types", "phone", "email",
    ],
}


def _is_filled(value) -> bool:
    """True если значение «заполнено» — не None, не пустая строка, не пустой список."""
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, list) and not value:
        return False
    return True


def _completion_pct(profile, category: str) -> int:
    """Процент заполненных required-полей профиля категории. 0 если профиль не создан."""
    if profile is None:
        return 0
    fields = _REQUIRED_FIELDS.get(category, [])
    if not fields:
        return 0
    filled = sum(1 for f in fields if _is_filled(getattr(profile, f, None)))
    return int(round(filled * 100 / len(fields)))


async def get_subscriptions(user_id: int) -> list[dict]:
    """Список подписок юзера + флаг profile_completed + completion_pct для каждой."""
    async with AsyncSessionLocal() as session:
        subs_res = await session.execute(
            select(UserCategorySubscription).where(UserCategorySubscription.user_id == user_id)
        )
        subs = list(subs_res.scalars().all())
        if not subs:
            return []
        result = []
        for sub in subs:
            model = CATEGORY_TO_MODEL[sub.category]
            prof_res = await session.execute(
                select(model).where(model.user_id == user_id)
            )
            profile = prof_res.scalar_one_or_none()
            result.append({
                "category": sub.category,
                "enabled": sub.enabled,
                "profile_completed": profile is not None and profile.completed_at is not None,
                "completion_pct": _completion_pct(profile, sub.category),
            })
        return result


async def set_subscriptions(user_id: int, categories: list[str]) -> list[dict]:
    """Создать строки подписок для каждой категории. Идемпотентно."""
    async with AsyncSessionLocal() as session:
        await upsert_user_in_session(session, user_id)
        for cat in categories:
            stmt = (
                pg_insert(UserCategorySubscription)
                .values(user_id=user_id, category=cat, enabled=True)
                .on_conflict_do_nothing(index_elements=["user_id", "category"])
            )
            await session.execute(stmt)
        await session.commit()
    return await get_subscriptions(user_id)


async def toggle_subscription(user_id: int, category: str, enabled: bool) -> bool:
    """Сменить enabled-флаг. Возвращает True если строка существовала."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(UserCategorySubscription).where(
                UserCategorySubscription.user_id == user_id,
                UserCategorySubscription.category == category,
            )
        )
        sub = res.scalar_one_or_none()
        if sub is None:
            return False
        sub.enabled = enabled
        await session.commit()
        return True


async def get_category_profile(user_id: int, category: str) -> Optional[dict]:
    """Вернуть профиль категории как dict (или None)."""
    model = CATEGORY_TO_MODEL.get(category)
    if model is None:
        return None
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(model).where(model.user_id == user_id))
        row = res.scalar_one_or_none()
        if row is None:
            return None
        return _profile_row_to_dict(row)


def _profile_row_to_dict(row) -> dict:
    """Сериализация профиль-row в dict (без SQLAlchemy-метаданных)."""
    return {
        c.name: getattr(row, c.name)
        for c in row.__table__.columns
    }


async def upsert_category_profile(
    user_id: int, category: str, data: dict
) -> Optional[dict]:
    """Draft-сохранение полей в профиль категории. Создаёт или обновляет."""
    model = CATEGORY_TO_MODEL.get(category)
    if model is None:
        return None
    async with AsyncSessionLocal() as session:
        await upsert_user_in_session(session, user_id)
        res = await session.execute(select(model).where(model.user_id == user_id))
        row = res.scalar_one_or_none()
        if row is None:
            row = model(user_id=user_id)
            session.add(row)
        for k, v in data.items():
            if hasattr(row, k) and k not in {"id", "user_id", "created_at", "updated_at", "completed_at"}:
                setattr(row, k, v)
        await session.commit()
        await session.refresh(row)
        return _profile_row_to_dict(row)


async def complete_category_profile(
    user_id: int, category: str
) -> tuple[Optional[dict], bool]:
    """Поставить completed_at=now(). Возвращает (profile_dict, was_first_time)."""
    model = CATEGORY_TO_MODEL.get(category)
    if model is None:
        return None, False
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(model).where(model.user_id == user_id))
        row = res.scalar_one_or_none()
        if row is None:
            return None, False
        was_first_time = row.completed_at is None
        row.completed_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(row)
        return _profile_row_to_dict(row), was_first_time


async def get_user_blacklist(user_id: int) -> list[str]:
    """Список запрещённых слов/фраз юзера."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(User.blacklisted_words).where(User.id == user_id)
        )
        words = res.scalar_one_or_none()
        return list(words or [])


async def set_user_blacklist(user_id: int, words: list[str]) -> list[str]:
    """Полная замена blacklist'а юзера. Чистит дубли и пустые строки."""
    seen: set[str] = set()
    cleaned: list[str] = []
    for w in words:
        s = (w or "").strip()
        if not s:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(s)
    async with AsyncSessionLocal() as session:
        await upsert_user_in_session(session, user_id)
        await session.execute(
            update(User).where(User.id == user_id).values(blacklisted_words=cleaned)
        )
        await session.commit()
    return cleaned


async def filter_users_by_blacklist(user_ids: list[int], text: str) -> list[int]:
    """Возвращает user_ids, у которых нет запрещённых слов в тексте.
    Сравнение case-insensitive."""
    if not user_ids:
        return []
    text_lower = (text or "").lower()
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(User.id, User.blacklisted_words).where(User.id.in_(user_ids))
        )
        ok: list[int] = []
        for uid, words in res.all():
            blocked = False
            for w in (words or []):
                ws = (w or "").strip().lower()
                if ws and ws in text_lower:
                    blocked = True
                    break
            if not blocked:
                ok.append(uid)
        return ok


_MSK_OFFSET = timedelta(hours=3)


def _msk_hour_now() -> int:
    """Текущий час в часовом поясе Europe/Moscow (UTC+3, без DST)."""
    return (datetime.now(timezone.utc) + _MSK_OFFSET).hour


def _is_night_window(hour: int, start: int, end: int) -> bool:
    """Час `hour` (0-23) попадает в ночной диапазон [start, end)?
    Если start <= end — обычный диапазон. Иначе wrap через полночь."""
    if start == end:
        return False  # пустой диапазон
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


# ---------- DELIVERY SETTINGS ----------


async def get_delivery_settings(user_id: int) -> dict:
    """Настройки доставки юзера. Если юзера нет — дефолты."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(
                User.delivery_mode,
                User.night_mode_enabled,
                User.night_start_hour,
                User.night_end_hour,
            ).where(User.id == user_id)
        )
        row = res.first()
        if row is None:
            return {
                "delivery_mode": "instant",
                "night_mode_enabled": False,
                "night_start_hour": 23,
                "night_end_hour": 9,
            }
        return {
            "delivery_mode": row[0],
            "night_mode_enabled": row[1],
            "night_start_hour": row[2],
            "night_end_hour": row[3],
        }


async def set_delivery_settings(
    user_id: int,
    *,
    delivery_mode: str,
    night_mode_enabled: bool,
    night_start_hour: int,
    night_end_hour: int,
) -> dict:
    if delivery_mode not in ("instant", "digest"):
        raise ValueError(f"Invalid delivery_mode: {delivery_mode}")
    if not (0 <= night_start_hour <= 23 and 0 <= night_end_hour <= 23):
        raise ValueError("hours must be 0..23")
    async with AsyncSessionLocal() as session:
        await upsert_user_in_session(session, user_id)
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                delivery_mode=delivery_mode,
                night_mode_enabled=night_mode_enabled,
                night_start_hour=night_start_hour,
                night_end_hour=night_end_hour,
            )
        )
        await session.commit()
    return await get_delivery_settings(user_id)


async def should_queue_for_user(user_id: int) -> bool:
    """True — если для этого юзера сейчас уведомление надо положить в
    очередь (digest или night-window). False — отправлять сразу."""
    s = await get_delivery_settings(user_id)
    if s["delivery_mode"] == "digest":
        return True
    if s["night_mode_enabled"] and _is_night_window(
        _msk_hour_now(), s["night_start_hour"], s["night_end_hour"]
    ):
        return True
    return False


# ---------- PENDING QUEUE ----------


async def enqueue_pending_notification(
    *,
    user_id: int,
    message_id: int,
    text_hash: str | None,
    matched_vacancy_ids: list[int] | None,
) -> bool:
    """Положить в очередь. Возвращает True если row создан, False если
    дубль (UNIQUE сработал)."""
    async with AsyncSessionLocal() as session:
        try:
            session.add(
                PendingNotification(
                    user_id=user_id,
                    message_id=message_id,
                    text_hash=text_hash,
                    matched_vacancy_ids=matched_vacancy_ids,
                )
            )
            await session.commit()
            return True
        except IntegrityError:
            await session.rollback()
            return False


async def pop_next_pending(user_id: int) -> Optional[dict]:
    """Достать самое раннее pending для юзера и удалить. Возвращает dict
    с message_id, text_hash, matched_vacancy_ids — или None если очередь пуста."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(PendingNotification)
            .where(PendingNotification.user_id == user_id)
            .order_by(PendingNotification.created_at.asc())
            .limit(1)
        )
        row = res.scalar_one_or_none()
        if row is None:
            return None
        result = {
            "message_id": row.message_id,
            "text_hash": row.text_hash,
            "matched_vacancy_ids": list(row.matched_vacancy_ids or []),
        }
        await session.delete(row)
        await session.commit()
        return result


async def count_pending(user_id: int) -> int:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(sa_func.count())
            .select_from(PendingNotification)
            .where(PendingNotification.user_id == user_id)
        )
        return int(res.scalar() or 0)


async def list_users_with_pending_in_morning() -> list[tuple[int, int]]:
    """Найти юзеров: night_mode_enabled=TRUE, текущий MSK-час == night_end_hour,
    есть pending, и night_digest_last_sent_at не сегодня. Возвращает [(user_id, count)]."""
    msk_now = datetime.now(timezone.utc) + _MSK_OFFSET
    msk_hour = msk_now.hour
    msk_today_start_utc = (msk_now.replace(hour=0, minute=0, second=0, microsecond=0)) - _MSK_OFFSET
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(
                User.id,
                sa_func.count(PendingNotification.id),
            )
            .join(
                PendingNotification,
                PendingNotification.user_id == User.id,
            )
            .where(
                User.night_mode_enabled.is_(True),
                User.night_end_hour == msk_hour,
                # last_sent_at NULL OR < сегодня MSK 00:00
                (User.night_digest_last_sent_at.is_(None))
                | (User.night_digest_last_sent_at < msk_today_start_utc),
            )
            .group_by(User.id)
        )
        return [(uid, cnt) for uid, cnt in res.all()]


async def mark_night_digest_sent(user_id: int) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(night_digest_last_sent_at=datetime.now(timezone.utc))
        )
        await session.commit()


async def list_legacy_unmigrated_users() -> list[int]:
    """Список user_id юзеров, заполнивших старую actor_profile анкету,
    но ещё не выбравших ни одну из новых категорий.

    Используется в админ-команде /broadcast_legacy чтобы разово сообщить
    им «анкета обновилась, пройдите заново»."""
    async with AsyncSessionLocal() as session:
        subbed_subquery = (
            select(UserCategorySubscription.user_id).distinct().subquery()
        )
        res = await session.execute(
            select(ActorProfile.user_id)
            .where(
                ActorProfile.completed_at.is_not(None),
                ActorProfile.user_id.notin_(select(subbed_subquery.c.user_id)),
            )
        )
        return list(res.scalars().all())


def _collect_suggestions(profiles: dict[str, dict]) -> dict[str, list]:
    """Собрать autocomplete-suggestions из профилей юзера.

    profiles: {category_code: {field: value, 'updated_at': dt}}
    Возвращает {field: [values...]} — только канонические скалярные поля,
    dedupe, сортировка по updated_at источника DESC.
    """
    by_field: dict[str, list[tuple[datetime, object]]] = {}
    for cat, data in profiles.items():
        updated = data.get("updated_at")
        if updated is None:
            continue
        for field, value in data.items():
            if field not in _SUGGESTION_FIELDS:
                continue
            if value is None or value == "":
                continue
            by_field.setdefault(field, []).append((updated, value))

    result: dict[str, list] = {}
    for field, items in by_field.items():
        items.sort(key=lambda x: x[0], reverse=True)
        seen = set()
        deduped: list = []
        for _, val in items:
            if val in seen:
                continue
            seen.add(val)
            deduped.append(val)
        result[field] = deduped
    return result


async def get_suggestions(user_id: int) -> dict[str, list]:
    """Собрать suggestions из всех 4 профилей юзера."""
    profiles: dict[str, dict] = {}
    async with AsyncSessionLocal() as session:
        for cat, model in CATEGORY_TO_MODEL.items():
            res = await session.execute(select(model).where(model.user_id == user_id))
            row = res.scalar_one_or_none()
            if row is not None:
                profiles[cat] = _profile_row_to_dict(row)
    return _collect_suggestions(profiles)
