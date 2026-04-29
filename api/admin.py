"""Admin-only endpoints: список анкет, история LLM-extract'а, статистика.

Все ручки требуют, чтобы telegram-user_id присутствовал в settings.admin_ids
(.env: ADMIN_IDS=...). Без этого FastAPI возвращает 403.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from api.auth import TelegramUser, admin_user
from db.models import ActorProfile, Message, Notification, Vacancy
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
    description: Optional[str] = None
    role_label: Optional[str] = None


class AdminMessage(BaseModel):
    id: int
    tg_chat_username: Optional[str] = None
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


# ---------- Endpoints ----------

@router.get("/stats", response_model=AdminStats)
async def stats(_: TelegramUser = Depends(admin_user)) -> AdminStats:
    async with AsyncSessionLocal() as session:
        profiles_total = (await session.execute(select(func.count(ActorProfile.user_id)))).scalar_one()
        profiles_completed = (
            await session.execute(
                select(func.count(ActorProfile.user_id)).where(ActorProfile.completed_at.is_not(None))
            )
        ).scalar_one()
        messages_total = (await session.execute(select(func.count(Message.id)))).scalar_one()
        messages_casting = (
            await session.execute(select(func.count(Message.id)).where(Message.is_casting.is_(True)))
        ).scalar_one()
        notifications_total = (await session.execute(select(func.count(Notification.id)))).scalar_one()
        notifications_success = (
            await session.execute(
                select(func.count(Notification.id)).where(Notification.success.is_(True))
            )
        ).scalar_one()

    return AdminStats(
        profiles_total=profiles_total,
        profiles_completed=profiles_completed,
        messages_total=messages_total,
        messages_casting=messages_casting,
        notifications_total=notifications_total,
        notifications_success=notifications_success,
    )


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
        # Подсчёт уведомлений на сообщение одним запросом — иначе N+1.
        notif_counts_stmt = (
            select(Notification.message_id, func.count(Notification.id).label("cnt"))
            .group_by(Notification.message_id)
        )
        notif_counts = {
            row.message_id: row.cnt
            for row in (await session.execute(notif_counts_stmt)).all()
        }

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

    return [
        AdminMessage(
            id=m.id,
            tg_chat_username=m.tg_chat_username,
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
                    description=v.description, role_label=v.role_label,
                )
                for v in m.vacancies
            ],
        )
        for m in rows
    ]
