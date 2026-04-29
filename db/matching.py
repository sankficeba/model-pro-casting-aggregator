"""Сопоставление извлечённого объявления с анкетами пользователей."""
from __future__ import annotations

from typing import Iterable

from sqlalchemy import select

from db.models import ActorProfile
from db.session import AsyncSessionLocal
from models.schemas import ExtractedData

# Минимальная уверенность LLM для рассылки. Ниже — игнорируем сообщение.
MIN_CONFIDENCE = 0.5


def _ranges_overlap(a_lo: int, a_hi: int, b_lo: int, b_hi: int) -> bool:
    return not (a_hi < b_lo or a_lo > b_hi)


def _intersect(a: Iterable[str], b: Iterable[str]) -> bool:
    return bool(set(a) & set(b))


def matches(profile: ActorProfile, data: ExtractedData) -> bool:
    """True, если анкета подходит под объявление.

    Если параметр в объявлении не указан — фильтр по нему не применяется
    (отдаём пользователю «возможно подходит», даже если LLM пропустил поле).
    Если параметр есть в объявлении и в профиле — должны совпасть/пересечься.
    """
    # Пол
    if data.gender and profile.gender and data.gender != profile.gender:
        return False

    # Возраст: пересечение диапазонов
    if data.age_min is not None or data.age_max is not None:
        msg_lo = data.age_min if data.age_min is not None else 0
        msg_hi = data.age_max if data.age_max is not None else 120
        prof_lo = profile.play_age_min if profile.play_age_min is not None else 0
        prof_hi = profile.play_age_max if profile.play_age_max is not None else 120
        if not _ranges_overlap(msg_lo, msg_hi, prof_lo, prof_hi):
            return False

    # Типы проектов: пересечение, если у обеих сторон что-то задано
    if data.project_types and profile.project_types:
        if not _intersect(data.project_types, profile.project_types):
            return False

    # Типы ролей
    if data.role_types and profile.role_types:
        if not _intersect(data.role_types, profile.role_types):
            return False

    # Ставка: если объявление предлагает меньше, чем требует пользователь — мимо
    if data.rate is not None and profile.min_rate is not None and data.rate < profile.min_rate:
        return False

    # Город: если указан и не совпадает — мимо, кроме случая когда пользователь
    # готов к командировкам.
    if data.city and profile.city:
        if data.city.lower() != profile.city.lower() and not profile.ready_for_travel:
            return False

    return True


async def find_matching_profiles(data: ExtractedData) -> list[int]:
    """Возвращает user_id'ы анкет, подходящих под объявление.

    Учитываем только анкеты, у которых уже было нажато «Завершить»
    (completed_at IS NOT NULL) — иначе будем спамить пользователей,
    которые ещё в процессе заполнения.
    """
    if not data.is_casting or data.confidence < MIN_CONFIDENCE:
        return []

    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(ActorProfile).where(ActorProfile.completed_at.is_not(None))
        )
        profiles = res.scalars().all()

    return [p.user_id for p in profiles if matches(p, data)]
