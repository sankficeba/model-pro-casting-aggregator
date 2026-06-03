"""Репозиторий профилей актёров."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from api.schemas import ProfileResponse, ProfileUpdate
from db.models import ActorProfile, User
from db.session import AsyncSessionLocal


def _completion_pct(p: ActorProfile) -> int:
    """Грубая оценка заполненности — по этапам со скринов (20/40/60/80/100)."""
    score = 0
    # Step 1: основная инфо
    if p.full_name and p.gender and p.city and p.actual_age is not None:
        score += 20
    # Step 2: типы кастингов
    if p.project_types and p.role_types:
        score += 20
    # Step 3: параметры подбора
    if p.height_cm and p.ethnicity and p.body_type and p.hair_color:
        score += 20
    # Step 4: проф. параметры (необязательная часть, но даём вес)
    if p.has_experience is not None and p.education:
        score += 15
    # Step 5: дополнительные данные (необязательно)
    if p.eye_color:
        score += 10
    # Step 6: контакты — email обязателен для финиша
    if p.email:
        score += 15
    return min(100, score)


def _to_response(p: ActorProfile) -> ProfileResponse:
    return ProfileResponse(
        user_id=p.user_id,
        full_name=p.full_name,
        gender=p.gender,  # type: ignore[arg-type]
        city=p.city,
        ready_for_travel=p.ready_for_travel,
        actual_age=p.actual_age,
        play_age_min=p.play_age_min,
        play_age_max=p.play_age_max,
        project_types=list(p.project_types or []),
        role_types=list(p.role_types or []),
        min_rate=p.min_rate,
        show_negotiable=p.show_negotiable,
        show_noncommercial=p.show_noncommercial,
        show_agency=p.show_agency,
        height_cm=p.height_cm,
        clothing_size=p.clothing_size,
        shoe_size=p.shoe_size,
        ethnicity=list(p.ethnicity or []),
        body_type=list(p.body_type or []),
        hair_color=p.hair_color,
        hair_length=p.hair_length,
        has_experience=p.has_experience,
        experience_text=p.experience_text,
        education=p.education,
        tax_status=p.tax_status,
        eye_color=p.eye_color,
        marks=list(p.marks or []),
        skills_sport=list(p.skills_sport or []),
        skills_dance=list(p.skills_dance or []),
        skills_vocal=list(p.skills_vocal or []),
        skills_instruments=list(p.skills_instruments or []),
        portfolio_url=p.portfolio_url,
        video_url=p.video_url,
        professional_url=p.professional_url,
        phone=p.phone,
        vk_url=p.vk_url,
        email=p.email,  # type: ignore[arg-type]
        completion_pct=_completion_pct(p),
    )


async def get_profile(user_id: int) -> Optional[ProfileResponse]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(ActorProfile).where(ActorProfile.user_id == user_id)
        )
        p = res.scalar_one_or_none()
        return _to_response(p) if p else None


async def mark_completed(user_id: int) -> tuple[Optional[ProfileResponse], bool]:
    """Отмечает профиль завершённым. Возвращает (профиль, was_first_time).

    was_first_time = True, если completed_at до этого был NULL
    (то есть пользователь завершает анкету впервые).
    Возвращает (None, False), если профиля нет.
    """
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(ActorProfile).where(ActorProfile.user_id == user_id)
        )
        p = res.scalar_one_or_none()
        if p is None:
            return None, False
        was_first_time = p.completed_at is None
        if was_first_time:
            p.completed_at = func.now()
            await session.commit()
            await session.refresh(p)
        return _to_response(p), was_first_time


async def upsert_profile(
    user_id: int, username: Optional[str], data: ProfileUpdate
) -> ProfileResponse:
    """Создать или обновить профиль. Параллельно гарантируем существование users-строки."""
    async with AsyncSessionLocal() as session:
        # 1. users — upsert (юзер мог открыть Mini App без /start у бота)
        user_stmt = pg_insert(User).values(id=user_id, username=username)
        user_stmt = user_stmt.on_conflict_do_update(
            index_elements=[User.id],
            set_={"username": username, "last_active": user_stmt.excluded.last_active},
        )
        await session.execute(user_stmt)

        # 2. actor_profiles — найти или создать, потом обновить поля
        existing = await session.execute(
            select(ActorProfile).where(ActorProfile.user_id == user_id)
        )
        p = existing.scalar_one_or_none()
        if p is None:
            p = ActorProfile(user_id=user_id)
            session.add(p)

        for field, value in data.model_dump(exclude_unset=False).items():
            setattr(p, field, value)

        await session.commit()
        await session.refresh(p)
        return _to_response(p)
