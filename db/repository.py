"""Репозиторий — высокоуровневые операции над моделями.
Используется userbot'ом и aiogram-ботом."""
from __future__ import annotations

from dataclasses import dataclass, field
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
    Favorite,
    Filter,
    GeneralProfile,
    Message,
    Notification,
    Payment,
    PendingNotification,
    Problem,
    User,
    UserCategorySubscription,
    Vacancy,
)
from db.session import AsyncSessionLocal
from models.schemas import PostExtraction, UserFilter


@dataclass
class ResponseProfile:
    """Данные профиля, необходимые для генерации отклика на вакансию."""
    category: str
    full_name: Optional[str] = None
    actual_age: Optional[int] = None
    phone: Optional[str] = None
    height_cm: Optional[int] = None
    clothing_size: Optional[int] = None
    shoe_size: Optional[int] = None
    experience_text: Optional[str] = None
    has_experience: Optional[bool] = None
    skills_sport: list[str] = field(default_factory=list)
    skills_dance: list[str] = field(default_factory=list)
    skills_vocal: list[str] = field(default_factory=list)
    skills_instruments: list[str] = field(default_factory=list)


def _orm_to_response_profile(p: object, category: str) -> ResponseProfile:
    return ResponseProfile(
        category=category,
        full_name=getattr(p, "full_name", None),
        actual_age=getattr(p, "actual_age", None),
        phone=getattr(p, "phone", None),
        height_cm=getattr(p, "height_cm", None),
        clothing_size=getattr(p, "clothing_size", None),
        shoe_size=getattr(p, "shoe_size", None),
        experience_text=getattr(p, "experience_text", None),
        has_experience=getattr(p, "has_experience", None),
        skills_sport=list(getattr(p, "skills_sport", None) or []),
        skills_dance=list(getattr(p, "skills_dance", None) or []),
        skills_vocal=list(getattr(p, "skills_vocal", None) or []),
        skills_instruments=list(getattr(p, "skills_instruments", None) or []),
    )


async def get_response_profile(user_id: int, category: str) -> Optional[ResponseProfile]:
    """Загружает per-category профиль пользователя для генерации отклика.

    Для creative-категории: пробует CreativeProfile, при отсутствии
    откатывается на legacy ActorProfile.
    """
    _models = {
        "creative": CreativeProfile,
        "event": EventProfile,
        "general": GeneralProfile,
        "admin": AdminProfile,
    }
    Model = _models.get(category)
    if Model is None:
        return None
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Model).where(Model.user_id == user_id))
        p = res.scalar_one_or_none()
        if p is not None:
            return _orm_to_response_profile(p, category)
        # Фолбэк для creative: пользователи со старой ActorProfile-анкетой
        if category == "creative":
            res2 = await session.execute(
                select(ActorProfile).where(ActorProfile.user_id == user_id)
            )
            ap = res2.scalar_one_or_none()
            if ap is not None:
                return _orm_to_response_profile(ap, category)
        return None


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
                            shooting_date=v.shooting_date,
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


def _parse_invite_ref(raw: str) -> str | None:
    """Если raw похож на invite-ссылку приватного канала (`+abc123`,
    `joinchat/abc123`, `t.me/+abc123`, полный URL), вернуть нормализованную
    форму `https://t.me/+abc123`. Иначе None.
    """
    s = raw.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    s = s.strip("/")
    if s.startswith("joinchat/"):
        h = s[len("joinchat/"):].split("/", 1)[0]
        return f"https://t.me/+{h}" if h else None
    if s.startswith("+"):
        h = s[1:].split("/", 1)[0]
        return f"https://t.me/+{h}" if h else None
    return None


def _parse_channel_ref(raw: str) -> tuple[str | None, int | None]:
    """Возвращает (username, tg_chat_id). Ровно одно поле не None.

    - `@my_channel` / `https://t.me/my_channel` → (`my_channel`, None)
    - `https://t.me/c/<id>[/<msg_id>]` → (None, -100<id>) — приватный канал.
    - invite-ссылки (+abc / joinchat/abc) обрабатываются отдельно через
      `_parse_invite_ref` (см. add_channel).
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
    if raw.startswith("+") or raw.startswith("joinchat/"):
        # Invite-ссылка не парсится этой функцией — каллер обязан проверить
        # invite через _parse_invite_ref ДО неё.
        return None, None
    # Если юзер вставил ссылку на конкретный пост (`t.me/foo/12345`), оставляем
    # только username — иначе мы храним «foo/12345» и Telegram не резолвит.
    raw = raw.split("/", 1)[0]
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
    """Добавить канал. Поддерживает три формы:
    - `@username` / `t.me/username` → public.
    - `t.me/c/<id>` → private с известным tg_chat_id.
    - `+abc123` / `t.me/+abc123` / `t.me/joinchat/abc123` → private invite.
      Сохраняем invite URL в `invite_link`; userbot вступит через
      `ImportChatInviteRequest` при следующем резолве и закэширует tg_chat_id.

    Если уже существует и active — None. Был неактивен — реактивируем.
    """
    invite_link = _parse_invite_ref(ref)
    username: str | None = None
    tg_chat_id: int | None = None
    if invite_link is None:
        username, tg_chat_id = _parse_channel_ref(ref)
        if username is None and tg_chat_id is None:
            return None
    async with AsyncSessionLocal() as session:
        if invite_link is not None:
            existing = await session.execute(
                select(Channel).where(Channel.invite_link == invite_link)
            )
        elif username is not None:
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
            invite_link=invite_link,
            added_by=added_by,
            active=True,
        )
        session.add(ch)
        await session.commit()
        await session.refresh(ch)
        return ch


async def set_channel_invite_link(ref: str, link: str | None) -> bool:
    """Записать invite_link на канал (для приватных каналов, чтобы кнопка
    «Подробнее» под уведомлением могла открывать его). True если запись
    обновлена."""
    username, tg_chat_id = _parse_channel_ref(ref)
    if username is None and tg_chat_id is None:
        return False
    async with AsyncSessionLocal() as session:
        if username is not None:
            stmt = select(Channel).where(Channel.username == username)
        else:
            stmt = select(Channel).where(Channel.tg_chat_id == tg_chat_id)
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return False
        row.invite_link = (link or None)
        await session.commit()
        return True


async def get_last_seen_msg_per_channel() -> dict[int, int]:
    """Возвращает {tg_chat_id: MAX(tg_message_id)} — последнее увиденное
    сообщение для каждого канала из таблицы messages. Используется
    pull-backup-циклом в userbot для warm-start."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Message.tg_chat_id, sa_func.max(Message.tg_message_id))
            .where(Message.tg_chat_id.is_not(None))
            .group_by(Message.tg_chat_id)
        )
        out: dict[int, int] = {}
        for chat_id, max_id in res.all():
            if chat_id is None or max_id is None:
                continue
            bare = abs(int(chat_id))
            if bare > 1_000_000_000_000:
                bare -= 1_000_000_000_000
            # Берём максимум, если для одного канала есть и bare, и -100 формы.
            prev = out.get(bare, 0)
            if int(max_id) > prev:
                out[bare] = int(max_id)
        return out


async def bulk_clear_joined_at(channel_ids: list[int]) -> int:
    """Сбросить joined_at для перечисленных каналов. Используется,
    когда верификация через iter_dialogs показывает что бот фактически
    не состоит в канале (хотя локальный флаг стоит). После сброса
    retry-цикл попробует JoinChannelRequest заново."""
    if not channel_ids:
        return 0
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            update(Channel)
            .where(Channel.id.in_(channel_ids))
            .values(joined_at=None)
        )
        await session.commit()
        return result.rowcount or 0


async def mark_channel_joined(channel_id: int) -> bool:
    """Установить channels.joined_at = NOW() — мы фактически вступили
    (JoinChannelRequest вернул успех / UserAlreadyParticipantError) либо
    подтвердили членство через ImportChatInvite."""
    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            select(Channel).where(Channel.id == channel_id)
        )).scalar_one_or_none()
        if row is None or row.joined_at is not None:
            return False
        row.joined_at = datetime.now(timezone.utc)
        await session.commit()
        return True


async def list_pending_join_channels() -> list[Channel]:
    """Активные каналы, к которым userbot ещё не вступил
    (joined_at IS NULL). Retry-цикл пытается вступить периодически."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Channel)
            .where(Channel.active.is_(True), Channel.joined_at.is_(None))
            .order_by(Channel.id)
        )
        return list(res.scalars().all())


async def cache_channel_tg_chat_id_by_invite(invite_link: str, tg_chat_id: int) -> bool:
    """Записать `entity.id` после ImportChatInvite для приватного канала
    (хранится в `channels.invite_link`). На следующем старте идём по id из
    session-кэша вместо повторного импорта приглашения."""
    if not invite_link:
        return False
    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            select(Channel).where(Channel.invite_link == invite_link)
        )).scalar_one_or_none()
        if row is None or row.tg_chat_id == tg_chat_id:
            return False
        row.tg_chat_id = tg_chat_id
        await session.commit()
        return True


async def cache_channel_tg_chat_id(username: str, tg_chat_id: int) -> bool:
    """После успешного резолва @username → entity сохраняем `entity.id` в
    `channels.tg_chat_id`, чтобы на следующих стартах резолвить из
    session-кэша по числу (без `ResolveUsernameRequest` → нет FloodWait).
    Сохраняем в bare-форме (как `messages.tg_chat_id`); Telethon
    `get_entity` принимает оба варианта."""
    norm = (username or "").lstrip("@").lower()
    if not norm:
        return False
    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            select(Channel).where(Channel.username == norm)
        )).scalar_one_or_none()
        if row is None or row.tg_chat_id == tg_chat_id:
            return False
        row.tg_chat_id = tg_chat_id
        await session.commit()
        return True


async def get_message_permalink(message_id: int) -> str | None:
    """Прямой URL на конкретное сообщение.
    - Public канал → `https://t.me/<username>/<msg_id>`.
    - Приватный → `https://t.me/c/<bare_chat_id>/<msg_id>`. Открывается у
      тех, кто уже в канале (для остальных будет пустой экран — поэтому
      кнопка «Ссылка на группу» отдельно даёт invite_link для входа).
    """
    async with AsyncSessionLocal() as session:
        msg = (await session.execute(
            select(Message).where(Message.id == message_id)
        )).scalar_one_or_none()
        if msg is None:
            return None
        if msg.tg_chat_username:
            return f"https://t.me/{msg.tg_chat_username}/{msg.tg_message_id}"
        if msg.tg_chat_id is not None:
            bare = abs(msg.tg_chat_id)
            if bare > 1_000_000_000_000:
                bare -= 1_000_000_000_000
            return f"https://t.me/c/{bare}/{msg.tg_message_id}"
        return None


async def get_message_text(message_id: int) -> str | None:
    """Вернуть оригинальный текст сообщения из БД."""
    async with AsyncSessionLocal() as session:
        return (await session.execute(
            select(Message.text).where(Message.id == message_id)
        )).scalar_one_or_none()


async def get_message_source_ids(
    message_id: int,
) -> tuple[int | None, str | None, int] | None:
    """Вернуть (tg_chat_id, tg_chat_username, tg_message_id) для сообщения."""
    async with AsyncSessionLocal() as session:
        msg = (await session.execute(
            select(Message).where(Message.id == message_id)
        )).scalar_one_or_none()
        if msg is None:
            return None
        return msg.tg_chat_id, msg.tg_chat_username, msg.tg_message_id


async def get_channel_link_for_message(message_id: int) -> tuple[str | None, str | None]:
    """Для message_id вернуть (link, channel_label).
    Логика:
    - если у Channel есть username → t.me/{username} (link на сам канал)
    - иначе если у Channel есть invite_link → он
    - иначе → (None, label) — фронт отрисует «ссылка не указана».
    label всегда заполнен (для алерта).
    """
    async with AsyncSessionLocal() as session:
        msg = (await session.execute(
            select(Message).where(Message.id == message_id)
        )).scalar_one_or_none()
        if msg is None:
            return None, None
        # У Message есть tg_chat_username → можно собрать ссылку прямо на пост
        if msg.tg_chat_username:
            link = f"https://t.me/{msg.tg_chat_username}/{msg.tg_message_id}"
            return link, f"@{msg.tg_chat_username}"
        # Иначе — поднимаем Channel по tg_chat_id
        if msg.tg_chat_id is not None:
            ch = (await session.execute(
                select(Channel).where(Channel.tg_chat_id == msg.tg_chat_id)
            )).scalar_one_or_none()
            if ch is not None:
                if ch.username:
                    return f"https://t.me/{ch.username}", f"@{ch.username}"
                if ch.invite_link:
                    return ch.invite_link, f"приватный канал #{ch.id}"
                return None, f"приватный канал #{ch.id}"
        return None, "источник"


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


async def get_matched_vacancy_ids(user_id: int, message_id: int) -> list[int]:
    """Восстановить список matched_vacancy_ids для пары (user_id, message_id):
    сначала пробуем последнюю Notification, потом PendingNotification.
    Если ничего нет — возвращаем []."""
    async with AsyncSessionLocal() as session:
        n = (await session.execute(
            select(Notification.matched_vacancy_ids)
            .where(
                Notification.user_id == user_id,
                Notification.message_id == message_id,
            )
        )).scalar_one_or_none()
        if n:
            return list(n)
        p = (await session.execute(
            select(PendingNotification.matched_vacancy_ids)
            .where(
                PendingNotification.user_id == user_id,
                PendingNotification.message_id == message_id,
            )
        )).scalar_one_or_none()
        if p:
            return list(p)
        return []


# ---------- FAVORITES ----------


async def add_favorite(
    user_id: int, message_id: int, matched_vacancy_ids: list[int],
) -> bool:
    """Добавить вакансию в избранное. True — реально вставлено,
    False — уже было (UNIQUE на (user_id, message_id))."""
    async with AsyncSessionLocal() as session:
        await upsert_user_in_session(session, user_id)
        try:
            session.add(Favorite(
                user_id=user_id,
                message_id=message_id,
                matched_vacancy_ids=list(matched_vacancy_ids or []),
            ))
            await session.commit()
            return True
        except IntegrityError:
            await session.rollback()
            return False


async def remove_favorite(user_id: int, message_id: int) -> bool:
    """Удалить из избранного. True если что-то реально удалено."""
    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            select(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.message_id == message_id,
            )
        )).scalar_one_or_none()
        if row is None:
            return False
        await session.delete(row)
        await session.commit()
        return True


async def is_favorited(user_id: int, message_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Favorite.id).where(
                Favorite.user_id == user_id,
                Favorite.message_id == message_id,
            )
        )
        return res.scalar_one_or_none() is not None


async def list_favorites(user_id: int) -> list[Favorite]:
    """Список избранного юзера (новые сверху). Подгружает связанные
    Message+Vacancy на следующих шагах."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Favorite)
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.created_at.desc())
        )
        return list(res.scalars().all())


async def prune_old_favorites(user_id: int) -> int:
    """Удалить старые избранные согласно user.favorites_retention_days.
    0 = не удалять. Возвращает кол-во удалённых строк."""
    async with AsyncSessionLocal() as session:
        u = (await session.execute(
            select(User.favorites_retention_days).where(User.id == user_id)
        )).scalar_one_or_none()
        days = int(u) if u is not None else 5
        if days <= 0:
            return 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        from sqlalchemy import delete as sa_delete
        result = await session.execute(
            sa_delete(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.created_at < cutoff,
            )
        )
        await session.commit()
        return result.rowcount or 0


async def get_favorites_retention_days(user_id: int) -> int:
    async with AsyncSessionLocal() as session:
        u = (await session.execute(
            select(User.favorites_retention_days).where(User.id == user_id)
        )).scalar_one_or_none()
        return int(u) if u is not None else 5


async def set_favorites_retention_days(user_id: int, days: int) -> bool:
    """Установить срок автоудаления. days=0 → не удалять. Допустимый
    диапазон 0..90."""
    if days < 0 or days > 90:
        return False
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(
                favorites_retention_days=days,
            )
        )
        await session.commit()
        return True


async def get_favorite(user_id: int, message_id: int) -> Optional[Favorite]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.message_id == message_id,
            )
        )
        return res.scalar_one_or_none()


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


# Глобальный blacklist (case-insensitive). Сообщение содержащее любую
# из фраз не рассылается ВСЕМ пользователям, независимо от per-user.
# Используется чтобы массово отсечь военную и подобную тематику.
#
# Длинные слова матчатся по корню (последние 2 буквы заменяются на
# \w* — учитывает русскую склоняемость: «службу»/«службой»/«служб»).
# Короткие (≤4 букв) и аббревиатуры — точно по границам слова.
GLOBAL_BLACKLIST_SUBSTRINGS = (
    # Безусловно военные термины, у которых НЕТ контекста актёрского
    # кастинга. То что может встречаться в фильмах/сериалах
    # («военнослужащий», «штурмовик», «артиллерист», «БПЛА») — НЕ
    # включаем в regex, потому что блокировали бы легитимные castings
    # массовки. Для них работает LLM-фильтр в промпте (категория 1).
    "сво",                       # «НЕ СВО», «на СВО»
    "спецоперация",
    "служба по контракту",       # «военная служба по контракту»
    "военкомат",
    "военный комиссариат",
    "военный билет",             # требуется для контракта
    "контрактник",
    "контрактная служба",
    "африканский корпус",
    "штурмовая бригада",          # подразделение, не киношный образ
    "мотострелковый полк",
    "единовременная выплата",     # ЕДВ за контракт
    "едв",
)


def text_has_global_blacklist(text: str) -> bool:
    """True если в тексте есть хоть одна фраза из глобального blacklist'а.
    Многословные фразы — слова разделяются \\s+. Для каждого слова >4
    букв режется хвост (-2 символа) и добавляется \\w* для матчинга
    русских склонений."""
    import re
    if not text:
        return False
    lower = text.lower()

    def _word_pattern(w: str) -> str:
        # Аббревиатуры (содержат только согласные/кратко) — точно.
        if len(w) <= 4:
            return re.escape(w)
        # Длинные слова — по корню. «контракту» → «контракт» + \w*.
        return re.escape(w[:-2]) + r"\w*"

    for phrase in GLOBAL_BLACKLIST_SUBSTRINGS:
        words = phrase.split()
        joined = r"\s+".join(_word_pattern(w) for w in words)
        # \b не работает для кириллицы в Python re, используем явные границы.
        pattern = r"(?:^|[^а-яa-z0-9])" + joined + r"(?:$|[^а-яa-z0-9])"
        if re.search(pattern, lower):
            return True
    return False


async def filter_users_by_blacklist(user_ids: list[int], text: str) -> list[int]:
    """Возвращает user_ids, у которых нет запрещённых слов в тексте
    И активен чат с ботом (bot_chat_active=True). Юзеры без живого
    чата отсекаются здесь же одним запросом — нет смысла слать
    нотификацию, если Telegram её всё равно отклонит."""
    if not user_ids:
        return []
    text_lower = (text or "").lower()
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(User.id, User.blacklisted_words).where(
                User.id.in_(user_ids),
                User.bot_chat_active.is_(True),
            )
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
                User.digest_daily_enabled,
                User.digest_daily_hour,
            ).where(User.id == user_id)
        )
        row = res.first()
        if row is None:
            return {
                "delivery_mode": "instant",
                "night_mode_enabled": False,
                "night_start_hour": 23,
                "night_end_hour": 9,
                "digest_daily_enabled": False,
                "digest_daily_hour": 20,
            }
        return {
            "delivery_mode": row[0],
            "night_mode_enabled": row[1],
            "night_start_hour": row[2],
            "night_end_hour": row[3],
            "digest_daily_enabled": row[4],
            "digest_daily_hour": row[5],
        }


async def set_delivery_settings(
    user_id: int,
    *,
    delivery_mode: str,
    night_mode_enabled: bool,
    night_start_hour: int,
    night_end_hour: int,
    digest_daily_enabled: bool,
    digest_daily_hour: int,
) -> dict:
    if delivery_mode not in ("instant", "digest"):
        raise ValueError(f"Invalid delivery_mode: {delivery_mode}")
    if not (0 <= night_start_hour <= 23 and 0 <= night_end_hour <= 23):
        raise ValueError("hours must be 0..23")
    if not 0 <= digest_daily_hour <= 23:
        raise ValueError("digest_daily_hour must be 0..23")
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
                digest_daily_enabled=digest_daily_enabled,
                digest_daily_hour=digest_daily_hour,
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
    """Считает pending-записи юзера, исключая те, чей text_hash уже
    отмечен в notifications (= при попытке отправки сработал бы
    UNIQUE-дедуп и юзер их всё равно не увидел бы). Это даёт честное
    число «осталось нерассмотренных» для шапки digest-сообщения."""
    from sqlalchemy import or_
    async with AsyncSessionLocal() as session:
        notified_hashes = (
            select(Notification.text_hash)
            .where(
                Notification.user_id == user_id,
                Notification.text_hash.is_not(None),
            )
        )
        notified_msg_ids = (
            select(Notification.message_id)
            .where(Notification.user_id == user_id)
        )
        res = await session.execute(
            select(sa_func.count())
            .select_from(PendingNotification)
            .where(
                PendingNotification.user_id == user_id,
                # Не считаем pending, чей text_hash уже отмечен в notifications
                or_(
                    PendingNotification.text_hash.is_(None),
                    ~PendingNotification.text_hash.in_(notified_hashes),
                ),
                # И не считаем pending, чей message_id уже отмечен в notifications.
                ~PendingNotification.message_id.in_(notified_msg_ids),
            )
        )
        return int(res.scalar() or 0)


async def mark_for_llm_retry(message_id: int) -> None:
    """Помечает сообщение для повторного LLM-вызова (нехватка баланса)."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Message)
            .where(Message.id == message_id)
            .values(llm_retry_needed=True)
        )
        await session.commit()


async def get_messages_for_llm_retry(limit: int = 50) -> list[tuple[int, str, str | None, str | None, int]]:
    """Сообщения с llm_retry_needed=True, порциями по `limit`.
    Возвращает [(id, text, text_hash, tg_chat_username, tg_message_id)]."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(
                Message.id,
                Message.text,
                Message.text_hash,
                Message.tg_chat_username,
                Message.tg_message_id,
            )
            .where(Message.llm_retry_needed.is_(True))
            .order_by(Message.received_at)
            .limit(limit)
        )
        return list(res.all())


async def apply_llm_retry(message_id: int, post: "PostExtraction") -> list[int]:
    """Обновляет сообщение результатом повторного LLM-вызова, создаёт
    вакансии и сбрасывает флаг retry. Возвращает список vacancy_id."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Message)
            .where(Message.id == message_id)
            .values(
                is_casting=post.is_casting,
                project_types=list(post.project_types),
                city=post.city,
                summary=post.summary,
                confidence=post.confidence,
                category=post.category,
                llm_retry_needed=False,
            )
        )
        vacancy_ids: list[int] = []
        if post.is_casting and post.vacancies:
            for idx, v in enumerate(post.vacancies):
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
                        shooting_date=v.shooting_date,
                    )
                    .on_conflict_do_nothing()
                    .returning(Vacancy.id)
                )
                vac_res = await session.execute(vac_stmt)
                vac_id = vac_res.scalar_one_or_none()
                if vac_id is not None:
                    vacancy_ids.append(vac_id)
        await session.commit()
        return vacancy_ids


async def list_users_with_pending_in_morning() -> list[tuple[int, int]]:
    """Найти юзеров: night_mode_enabled=TRUE, текущий MSK-час == night_end_hour,
    есть pending, и night_digest_last_sent_at не сегодня. Возвращает [(user_id, count)].
    Счёт идентичен count_pending(): исключает уже отправленные (по text_hash / message_id)."""
    from sqlalchemy import or_
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
                # Тот же фильтр, что в count_pending(): не учитываем уже отправленные
                or_(
                    PendingNotification.text_hash.is_(None),
                    ~PendingNotification.text_hash.in_(
                        select(Notification.text_hash).where(
                            Notification.user_id == User.id,
                            Notification.text_hash.is_not(None),
                        )
                    ),
                ),
                ~PendingNotification.message_id.in_(
                    select(Notification.message_id).where(
                        Notification.user_id == User.id,
                    )
                ),
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


async def list_users_for_daily_digest_due() -> list[tuple[int, int]]:
    """Юзеры в digest-режиме с включённой ежедневной плашкой, у которых
    текущий MSK-час == digest_daily_hour, есть pending, и daily-digest
    сегодня ещё не уходил. Возвращает [(user_id, count)].
    Счёт идентичен count_pending(): исключает уже отправленные (по text_hash / message_id)."""
    from sqlalchemy import or_
    msk_now = datetime.now(timezone.utc) + _MSK_OFFSET
    msk_hour = msk_now.hour
    msk_today_start_utc = (
        msk_now.replace(hour=0, minute=0, second=0, microsecond=0)
    ) - _MSK_OFFSET
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
                User.delivery_mode == "digest",
                User.digest_daily_enabled.is_(True),
                User.digest_daily_hour == msk_hour,
                (User.digest_daily_last_sent_at.is_(None))
                | (User.digest_daily_last_sent_at < msk_today_start_utc),
                # Тот же фильтр, что в count_pending(): не учитываем уже отправленные
                or_(
                    PendingNotification.text_hash.is_(None),
                    ~PendingNotification.text_hash.in_(
                        select(Notification.text_hash).where(
                            Notification.user_id == User.id,
                            Notification.text_hash.is_not(None),
                        )
                    ),
                ),
                ~PendingNotification.message_id.in_(
                    select(Notification.message_id).where(
                        Notification.user_id == User.id,
                    )
                ),
            )
            .group_by(User.id)
        )
        return [(uid, cnt) for uid, cnt in res.all()]


async def mark_daily_digest_sent(user_id: int) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(digest_daily_last_sent_at=datetime.now(timezone.utc))
        )
        await session.commit()


VALID_BROADCAST_FILTERS = {"all", "creative", "event", "general", "admin"}


async def set_broadcast_pending(
    user_id: int,
    filter_code: str,
    *,
    age_min: int | None = None,
    age_max: int | None = None,
    height_min: int | None = None,
    height_max: int | None = None,
    name_query: str | None = None,
) -> None:
    if filter_code not in VALID_BROADCAST_FILTERS:
        raise ValueError(f"Invalid broadcast filter: {filter_code}")
    payload: dict = {}
    for key, val in (
        ("age_min", age_min),
        ("age_max", age_max),
        ("height_min", height_min),
        ("height_max", height_max),
    ):
        if val is not None:
            payload[key] = int(val)
    nq = (name_query or "").strip()
    if nq:
        payload["name_query"] = nq
    async with AsyncSessionLocal() as session:
        await upsert_user_in_session(session, user_id)
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                broadcast_pending_filter=filter_code,
                broadcast_pending_at=datetime.now(timezone.utc),
                broadcast_pending_payload=payload or None,
            )
        )
        await session.commit()


async def get_broadcast_pending(user_id: int) -> Optional[dict]:
    """Возвращает {filter, age_min?, age_max?, height_min?, height_max?, name_query?}
    или None, если pending-рассылки нет."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(
                User.broadcast_pending_filter,
                User.broadcast_pending_payload,
            ).where(User.id == user_id)
        )
        row = res.first()
    if row is None or row[0] is None:
        return None
    payload = dict(row[1] or {})
    payload["filter"] = row[0]
    return payload


async def clear_broadcast_pending(user_id: int) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                broadcast_pending_filter=None,
                broadcast_pending_at=None,
                broadcast_pending_payload=None,
            )
        )
        await session.commit()


async def list_broadcast_audience(
    filter_code: str,
    *,
    age_min: int | None = None,
    age_max: int | None = None,
    height_min: int | None = None,
    height_max: int | None = None,
    name_query: str | None = None,
) -> list[int]:
    """Список user_id для рассылки.

    filter_code: scope аудитории (all/creative/event/general/admin).
    Доп.фильтры (возраст/рост/ФИО) живут в per-category профилях. Если
    заданы — для scope=all берём union по 4 профильным таблицам с enabled
    подпиской. Без доп.фильтров и scope=all — все юзеры из users.
    """
    if filter_code not in VALID_BROADCAST_FILTERS:
        raise ValueError(f"Invalid broadcast filter: {filter_code}")
    name_query = (name_query or "").strip() or None
    has_demographic = any(
        v is not None for v in (age_min, age_max, height_min, height_max, name_query)
    )
    if filter_code == "all" and not has_demographic:
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(User.id).where(User.bot_chat_active.is_(True))
            )
            return [int(uid) for uid in res.scalars().all()]

    categories = (
        ["creative", "event", "general", "admin"]
        if filter_code == "all"
        else [filter_code]
    )
    profile_classes: dict[str, type] = {
        "creative": CreativeProfile,
        "event": EventProfile,
        "general": GeneralProfile,
        "admin": AdminProfile,
    }
    user_ids: set[int] = set()
    async with AsyncSessionLocal() as session:
        for cat in categories:
            profile_cls = profile_classes[cat]
            has_height = hasattr(profile_cls, "height_cm")
            # Если задан height-фильтр, а у этой категории нет роста — пропускаем
            if (height_min is not None or height_max is not None) and not has_height:
                continue
            stmt = (
                select(profile_cls.user_id)
                .join(
                    UserCategorySubscription,
                    (UserCategorySubscription.user_id == profile_cls.user_id)
                    & (UserCategorySubscription.category == cat)
                    & (UserCategorySubscription.enabled.is_(True)),
                )
            )
            if age_min is not None:
                stmt = stmt.where(profile_cls.actual_age >= age_min)
            if age_max is not None:
                stmt = stmt.where(profile_cls.actual_age <= age_max)
            if height_min is not None and has_height:
                stmt = stmt.where(profile_cls.height_cm >= height_min)
            if height_max is not None and has_height:
                stmt = stmt.where(profile_cls.height_cm <= height_max)
            if name_query is not None:
                stmt = stmt.where(profile_cls.full_name.ilike(f"%{name_query}%"))
            res = await session.execute(stmt)
            user_ids.update(int(uid) for uid in res.scalars().all())
        # Финальная фильтрация: отсекаем юзеров без активного чата с ботом.
        if user_ids:
            res = await session.execute(
                select(User.id).where(
                    User.id.in_(user_ids),
                    User.bot_chat_active.is_(True),
                )
            )
            user_ids = {int(uid) for uid in res.scalars().all()}
    return sorted(user_ids)


async def count_broadcast_audience(
    filter_code: str,
    **kwargs,
) -> int:
    return len(await list_broadcast_audience(filter_code, **kwargs))


async def get_extended_admin_stats() -> dict:
    """Расширенная статистика для админки: считает количество юзеров,
    тех у кого digest, и pending-очередь."""
    async with AsyncSessionLocal() as session:
        users_total = (
            await session.execute(select(sa_func.count(User.id)))
        ).scalar_one()
        users_digest = (
            await session.execute(
                select(sa_func.count(User.id)).where(
                    User.delivery_mode == "digest"
                )
            )
        ).scalar_one()
        pending_total = (
            await session.execute(
                select(sa_func.count(PendingNotification.id))
            )
        ).scalar_one()
        # Активные подписки по категориям
        subs_by_cat_res = await session.execute(
            select(
                UserCategorySubscription.category,
                sa_func.count(UserCategorySubscription.id),
            )
            .where(UserCategorySubscription.enabled.is_(True))
            .group_by(UserCategorySubscription.category)
        )
        subs_by_category = {row[0]: int(row[1]) for row in subs_by_cat_res.all()}
    return {
        "users_total": int(users_total),
        "users_digest": int(users_digest),
        "pending_notifications_total": int(pending_total),
        "active_subscriptions_by_category": subs_by_category,
    }


# ---------- SUBSCRIPTIONS ----------


async def start_trial_if_first_time(user_id: int, trial_days: int) -> Optional[datetime]:
    """Если у юзера ещё не запускался trial — установить trial_started_at=now()
    и subscription_active_until=now()+trial_days. Возвращает active_until
    (новое или существующее)."""
    async with AsyncSessionLocal() as session:
        await upsert_user_in_session(session, user_id)
        res = await session.execute(
            select(User.trial_started_at, User.subscription_active_until)
            .where(User.id == user_id)
        )
        row = res.first()
        if row is None:
            return None
        if row[0] is not None:
            return row[1]  # уже был trial — ничего не трогаем
        now = datetime.now(timezone.utc)
        active_until = now + timedelta(days=trial_days)
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                trial_started_at=now,
                subscription_active_until=active_until,
                last_expiry_reminder_stage=None,
            )
        )
        await session.commit()
        return active_until


async def get_subscription_status(user_id: int) -> dict:
    """Возвращает {active_until, days_left, is_active, trial_started_at}."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(
                User.subscription_active_until,
                User.trial_started_at,
            ).where(User.id == user_id)
        )
        row = res.first()
    now = datetime.now(timezone.utc)
    if row is None:
        return {
            "active_until": None,
            "days_left": 0,
            "is_active": False,
            "trial_started_at": None,
        }
    active_until: Optional[datetime] = row[0]
    trial_started_at: Optional[datetime] = row[1]
    is_active = active_until is not None and active_until > now
    days_left = 0
    if is_active and active_until is not None:
        delta = active_until - now
        days_left = max(0, (delta.total_seconds() + 86399) // 86400)
        days_left = int(days_left)
    return {
        "active_until": active_until,
        "days_left": days_left,
        "is_active": is_active,
        "trial_started_at": trial_started_at,
    }


async def extend_subscription(user_id: int, days: int) -> datetime:
    """Продлить подписку на N дней. Если уже истекла — отсчёт с now().
    Сбрасывает last_expiry_reminder_stage. Возвращает новый active_until."""
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        await upsert_user_in_session(session, user_id)
        res = await session.execute(
            select(User.subscription_active_until).where(User.id == user_id)
        )
        current: Optional[datetime] = res.scalar_one_or_none()
        base = current if current and current > now else now
        new_active_until = base + timedelta(days=days)
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                subscription_active_until=new_active_until,
                last_expiry_reminder_stage=None,
                last_notify_after_expiry_at=None,
            )
        )
        await session.commit()
        return new_active_until


async def list_users_for_expiry_reminder(stage: str) -> list[tuple[int, datetime]]:
    """Юзеры, которым надо отправить напоминалку для конкретной стадии.

    stage ∈ {"2d","1d","3h"}. Возвращает (user_id, active_until).
    Условие: active_until ∈ (now+window_low, now+window_high] и
    last_expiry_reminder_stage != stage и не более ранняя стадия.
    """
    if stage not in ("2d", "1d", "3h"):
        raise ValueError(f"Invalid stage: {stage}")
    now = datetime.now(timezone.utc)
    # Окна — закрытое сверху, открытое снизу. «2d» = expires within (1d, 2d].
    windows = {
        "2d": (timedelta(days=1), timedelta(days=2)),
        "1d": (timedelta(hours=3), timedelta(days=1)),
        "3h": (timedelta(seconds=0), timedelta(hours=3)),
    }
    low, high = windows[stage]
    cutoff_low = now + low
    cutoff_high = now + high
    # Не слать одну и ту же стадию повторно. Также не "откатываемся" назад
    # с более поздней стадии: если уже отправлено "3h", не слать "1d"/"2d".
    blocked_stages = {
        "2d": ("2d", "1d", "3h"),
        "1d": ("1d", "3h"),
        "3h": ("3h",),
    }[stage]
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(User.id, User.subscription_active_until)
            .where(
                User.subscription_active_until.is_not(None),
                User.subscription_active_until > cutoff_low,
                User.subscription_active_until <= cutoff_high,
                (User.last_expiry_reminder_stage.is_(None))
                | (User.last_expiry_reminder_stage.notin_(blocked_stages)),
            )
        )
        return [(int(uid), au) for uid, au in res.all()]


async def mark_expiry_reminder_sent(user_id: int, stage: str) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_expiry_reminder_stage=stage)
        )
        await session.commit()


async def is_subscription_active(user_id: int) -> bool:
    s = await get_subscription_status(user_id)
    return bool(s["is_active"])


async def should_throttle_after_expiry(user_id: int) -> bool:
    """True если за последние 24ч юзеру с истёкшей подпиской уже улетело
    одно уведомление (degraded mode «1 в день»)."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(User.last_notify_after_expiry_at).where(User.id == user_id)
        )
        last: Optional[datetime] = res.scalar_one_or_none()
    if last is None:
        return False
    return (datetime.now(timezone.utc) - last) < timedelta(hours=24)


async def record_after_expiry_send(user_id: int) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_notify_after_expiry_at=datetime.now(timezone.utc))
        )
        await session.commit()


# ---------- PAYMENTS ----------


async def insert_payment_pending(
    *,
    user_id: int,
    idempotency_key: str,
    amount_rub: int,
    days: int,
) -> int:
    async with AsyncSessionLocal() as session:
        p = Payment(
            user_id=user_id,
            idempotency_key=idempotency_key,
            amount_rub=amount_rub,
            days=days,
            status="pending",
        )
        session.add(p)
        await session.commit()
        await session.refresh(p)
        return p.id


async def attach_yk_payment_id(payment_id: int, yk_payment_id: str) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Payment)
            .where(Payment.id == payment_id)
            .values(yk_payment_id=yk_payment_id)
        )
        await session.commit()


async def get_payment_by_yk_id(yk_payment_id: str) -> Optional[Payment]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Payment).where(Payment.yk_payment_id == yk_payment_id)
        )
        p = res.scalar_one_or_none()
        if p is not None:
            session.expunge(p)
        return p


async def mark_payment_status(yk_payment_id: str, status: str) -> bool:
    """Идемпотентно обновляет статус. Возвращает True если был апдейт
    с pending → succeeded (то есть нужно продлить подписку именно сейчас)."""
    if status not in ("succeeded", "canceled"):
        raise ValueError(f"Invalid payment status: {status}")
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Payment).where(Payment.yk_payment_id == yk_payment_id)
        )
        p = res.scalar_one_or_none()
        if p is None:
            return False
        was_pending = p.status == "pending"
        p.status = status
        await session.commit()
        return was_pending and status == "succeeded"


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
    """Собрать suggestions из всех 4 профилей юзера. 4 запроса идут
    параллельно через gather — ~50мс вместо ~200мс на последовательных."""
    import asyncio as _asyncio

    async def _fetch_one(cat: str, model) -> tuple[str, Optional[dict]]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(model).where(model.user_id == user_id)
            )
            row = res.scalar_one_or_none()
            return cat, _profile_row_to_dict(row) if row is not None else None

    results = await _asyncio.gather(
        *(_fetch_one(cat, model) for cat, model in CATEGORY_TO_MODEL.items())
    )
    profiles: dict[str, dict] = {
        cat: data for cat, data in results if data is not None
    }
    return _collect_suggestions(profiles)


# ---------- PROBLEMS ----------

async def mark_user_bot_chat_inactive(user_id: int) -> bool:
    """Помечаем юзера как недостижимого ботом: больше не пытаемся слать
    рассылки/нотификации до тех пор, пока он сам не вернётся в чат."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(bot_chat_active=False)
        )
        await session.commit()
        return True


async def mark_user_bot_chat_active(user_id: int) -> bool:
    """Восстановить флаг при успешной отправке (юзер вернулся / разблокировал)."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User).where(User.id == user_id, User.bot_chat_active.is_(False))
            .values(bot_chat_active=True)
        )
        await session.commit()
        return True


def is_bot_chat_dead_error(text: str) -> bool:
    """True если текст ошибки Telegram Bot API указывает на отсутствие
    активного чата (chat not found / blocked / deactivated)."""
    if not text:
        return False
    t = text.lower()
    return (
        "chat not found" in t
        or "bot was blocked by the user" in t
        or "user is deactivated" in t
        or "bots can't send messages to bots" in t
    )


async def get_user_by_id(user_id: int) -> Optional[User]:
    async with AsyncSessionLocal() as session:
        return (await session.execute(
            select(User).where(User.id == user_id)
        )).scalar_one_or_none()


async def create_problem(user_id: int, text: str) -> Problem:
    async with AsyncSessionLocal() as session:
        p = Problem(user_id=user_id, text=text)
        session.add(p)
        await session.commit()
        await session.refresh(p)
        return p


async def get_problem(problem_id: int) -> Optional[Problem]:
    async with AsyncSessionLocal() as session:
        return (await session.execute(
            select(Problem).where(Problem.id == problem_id)
        )).scalar_one_or_none()


async def list_active_problems() -> list[Problem]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Problem)
            .where(Problem.resolved.is_(False))
            .order_by(Problem.created_at.desc())
        )
        return list(res.scalars().all())


async def resolve_problem(problem_id: int) -> bool:
    """True, если статус действительно поменялся (был активен)."""
    async with AsyncSessionLocal() as session:
        p = (await session.execute(
            select(Problem).where(Problem.id == problem_id)
        )).scalar_one_or_none()
        if p is None or p.resolved:
            return False
        p.resolved = True
        p.resolved_at = datetime.now(timezone.utc)
        await session.commit()
        return True
