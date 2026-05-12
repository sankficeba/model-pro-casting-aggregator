"""Admin-only endpoints: список анкет, история LLM-extract'а, статистика.

Все ручки требуют, чтобы telegram-user_id присутствовал в settings.admin_ids
(.env: ADMIN_IDS=...). Без этого FastAPI возвращает 403.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from api.auth import TelegramUser, admin_user
from config import settings
from db import repository as repo
from db.models import ActorProfile, Message, Notification
from db.session import AsyncSessionLocal

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------- Schemas ----------

class AdminProfile(BaseModel):
    user_id: int
    full_name: Optional[str] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    actual_age: Optional[int] = None
    project_types: list[str] = []
    role_types: list[str] = []
    email: Optional[str] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime


class AdminVacancy(BaseModel):
    id: int
    idx: int
    role_types: list[str] = []
    gender: Optional[str] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    rate: Optional[int] = None
    ethnicity: list[str] = []
    height_min: Optional[int] = None
    height_max: Optional[int] = None
    body_type: list[str] = []
    hair_color: list[str] = []
    hair_length: list[str] = []
    description: Optional[str] = None
    role_label: Optional[str] = None


class AdminMessage(BaseModel):
    id: int
    tg_chat_username: Optional[str] = None
    tg_chat_id: Optional[int] = None
    tg_message_id: int
    text: str
    is_casting: bool
    project_types: list[str] = []
    city: Optional[str] = None
    summary: Optional[str] = None
    confidence: float
    received_at: datetime
    notified_count: int = Field(0, description="Сколько пользователей получило уведомление")
    vacancies: list[AdminVacancy] = []


class AdminStats(BaseModel):
    profiles_total: int
    profiles_completed: int
    messages_total: int
    messages_casting: int
    notifications_total: int
    notifications_success: int
    users_total: int
    users_digest: int
    pending_notifications_total: int
    active_subscriptions_by_category: dict[str, int]


BroadcastFilter = Literal["all", "creative", "event", "general", "admin"]


class BroadcastFilterBody(BaseModel):
    filter: BroadcastFilter = "all"
    age_min: Optional[int] = Field(default=None, ge=0, le=120)
    age_max: Optional[int] = Field(default=None, ge=0, le=120)
    height_min: Optional[int] = Field(default=None, ge=50, le=250)
    height_max: Optional[int] = Field(default=None, ge=50, le=250)
    name_query: Optional[str] = Field(default=None, max_length=128)


class BroadcastAudienceResponse(BaseModel):
    filter: BroadcastFilter
    count: int


class BroadcastStartResponse(BaseModel):
    ok: bool
    audience_count: int


# ---------- Endpoints ----------

@router.get("/stats", response_model=AdminStats)
async def stats(_: TelegramUser = Depends(admin_user)) -> AdminStats:
    """Параллелим 6 COUNT-запросов + extra через gather: было ~6 ×
    последовательных roundtrip'ов, стало 1 окно ~ один longest count."""
    import asyncio as _asyncio

    async def _count(stmt) -> int:
        async with AsyncSessionLocal() as session:
            return (await session.execute(stmt)).scalar_one()

    (
        profiles_total,
        profiles_completed,
        messages_total,
        messages_casting,
        notifications_total,
        notifications_success,
        extra,
    ) = await _asyncio.gather(
        _count(select(func.count(ActorProfile.user_id))),
        _count(select(func.count(ActorProfile.user_id)).where(
            ActorProfile.completed_at.is_not(None)
        )),
        _count(select(func.count(Message.id))),
        _count(select(func.count(Message.id)).where(Message.is_casting.is_(True))),
        _count(select(func.count(Notification.id))),
        _count(select(func.count(Notification.id)).where(
            Notification.success.is_(True)
        )),
        repo.get_extended_admin_stats(),
    )
    return AdminStats(
        profiles_total=profiles_total,
        profiles_completed=profiles_completed,
        messages_total=messages_total,
        messages_casting=messages_casting,
        notifications_total=notifications_total,
        notifications_success=notifications_success,
        users_total=extra["users_total"],
        users_digest=extra["users_digest"],
        pending_notifications_total=extra["pending_notifications_total"],
        active_subscriptions_by_category=extra["active_subscriptions_by_category"],
    )


def _filter_kwargs(body: BroadcastFilterBody) -> dict:
    return {
        "age_min": body.age_min,
        "age_max": body.age_max,
        "height_min": body.height_min,
        "height_max": body.height_max,
        "name_query": body.name_query,
    }


def _filter_summary(body: BroadcastFilterBody) -> list[str]:
    parts: list[str] = []
    if body.age_min is not None or body.age_max is not None:
        if body.age_min is not None and body.age_max is not None:
            parts.append(f"возраст {body.age_min}–{body.age_max}")
        elif body.age_min is not None:
            parts.append(f"возраст от {body.age_min}")
        else:
            parts.append(f"возраст до {body.age_max}")
    if body.height_min is not None or body.height_max is not None:
        if body.height_min is not None and body.height_max is not None:
            parts.append(f"рост {body.height_min}–{body.height_max} см")
        elif body.height_min is not None:
            parts.append(f"рост от {body.height_min} см")
        else:
            parts.append(f"рост до {body.height_max} см")
    if body.name_query:
        parts.append(f'ФИО содержит «{body.name_query}»')
    return parts


@router.post("/broadcast/audience", response_model=BroadcastAudienceResponse)
async def broadcast_audience(
    body: BroadcastFilterBody,
    _: TelegramUser = Depends(admin_user),
) -> BroadcastAudienceResponse:
    count = await repo.count_broadcast_audience(body.filter, **_filter_kwargs(body))
    return BroadcastAudienceResponse(filter=body.filter, count=count)


@router.post("/broadcast/start", response_model=BroadcastStartResponse)
async def broadcast_start(
    body: BroadcastFilterBody,
    user: TelegramUser = Depends(admin_user),
) -> BroadcastStartResponse:
    """Поставить у админа pending-state и попросить его прислать в чат
    сообщение для рассылки. Mini App после этого закрывается."""
    audience = await repo.count_broadcast_audience(body.filter, **_filter_kwargs(body))
    if audience == 0:
        raise HTTPException(
            status_code=400,
            detail="В выбранной аудитории сейчас 0 пользователей.",
        )
    # Сохраняем фильтры в БД, чтобы бот при копировании сообщения знал
    # точную аудиторию (а не пересчитывал её по одному только scope).
    await repo.set_broadcast_pending(user.id, body.filter, **_filter_kwargs(body))

    scope_label = {
        "all": "всем пользователям",
        "creative": "юзерам с подпиской «Творческие позиции»",
        "event": "юзерам с подпиской «Event-персонал»",
        "general": "юзерам с подпиской «Разнорабочие»",
        "admin": "юзерам с подпиской «Администрирование»",
    }[body.filter]
    extras = _filter_summary(body)
    extras_str = (" (" + ", ".join(extras) + ")") if extras else ""

    text = (
        "📢 <b>Готово к рассылке</b>\n\n"
        f"Сейчас отправь следующим сообщением то, что хочешь разослать "
        f"<b>{scope_label}</b>{extras_str} — {audience} чел. Можно текст, фото, "
        f"видео, гифку с форматированием и премиум-эмодзи.\n\n"
        "Отмена: /cancel"
    )
    url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                url,
                json={
                    "chat_id": user.id,
                    "text": text,
                    "parse_mode": "HTML",
                },
            )
            if r.status_code != 200:
                logger.warning(
                    "broadcast_start: prompt sendMessage failed: {} {}",
                    r.status_code, r.text,
                )
    except httpx.HTTPError as e:
        logger.warning("broadcast_start: prompt sendMessage error: {}", e)

    return BroadcastStartResponse(ok=True, audience_count=audience)


@router.get("/profiles", response_model=list[AdminProfile])
async def list_profiles(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: TelegramUser = Depends(admin_user),
) -> list[AdminProfile]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(ActorProfile)
            .order_by(ActorProfile.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = res.scalars().all()
    return [
        AdminProfile(
            user_id=p.user_id,
            full_name=p.full_name,
            gender=p.gender,
            city=p.city,
            actual_age=p.actual_age,
            project_types=list(p.project_types or []),
            role_types=list(p.role_types or []),
            email=p.email,
            completed_at=p.completed_at,
            updated_at=p.updated_at,
        )
        for p in rows
    ]


@router.get("/messages", response_model=list[AdminMessage])
async def list_messages(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    casting_only: bool = Query(False),
    _: TelegramUser = Depends(admin_user),
) -> list[AdminMessage]:
    async with AsyncSessionLocal() as session:
        # Сначала достаём страницу сообщений, потом считаем уведомления
        # только для них — иначе при росте notifications таблица сканится
        # вся каждый раз.
        msg_stmt = (
            select(Message)
            .options(selectinload(Message.vacancies))
            .order_by(Message.id.desc())
            .limit(limit)
            .offset(offset)
        )
        if casting_only:
            msg_stmt = msg_stmt.where(Message.is_casting.is_(True))
        res = await session.execute(msg_stmt)
        rows = res.scalars().all()

        page_ids = [m.id for m in rows]
        notif_counts: dict[int, int] = {}
        if page_ids:
            notif_counts_stmt = (
                select(Notification.message_id, func.count(Notification.id).label("cnt"))
                .where(Notification.message_id.in_(page_ids))
                .group_by(Notification.message_id)
            )
            notif_counts = {
                row.message_id: row.cnt
                for row in (await session.execute(notif_counts_stmt)).all()
            }

    return [
        AdminMessage(
            id=m.id,
            tg_chat_username=m.tg_chat_username,
            tg_chat_id=m.tg_chat_id,
            tg_message_id=m.tg_message_id,
            text=m.text,
            is_casting=m.is_casting,
            project_types=list(m.project_types or []),
            city=m.city,
            summary=m.summary,
            confidence=m.confidence,
            received_at=m.received_at,
            notified_count=notif_counts.get(m.id, 0),
            vacancies=[
                AdminVacancy(
                    id=v.id, idx=v.idx,
                    role_types=list(v.role_types or []),
                    gender=v.gender, age_min=v.age_min, age_max=v.age_max,
                    rate=v.rate,
                    ethnicity=list(v.ethnicity or []),
                    height_min=v.height_min, height_max=v.height_max,
                    body_type=list(v.body_type or []),
                    hair_color=list(v.hair_color or []),
                    hair_length=list(v.hair_length or []),
                    description=v.description, role_label=v.role_label,
                )
                for v in m.vacancies
            ],
        )
        for m in rows
    ]
