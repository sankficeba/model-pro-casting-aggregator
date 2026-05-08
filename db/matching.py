"""Сопоставление извлечённого объявления с анкетами пользователей."""
from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.models import CreativeProfile, Message, UserCategorySubscription, Vacancy
from db.session import AsyncSessionLocal
from models.schemas import PostExtraction, VacancyExtraction

# Минимальная уверенность LLM для рассылки. Ниже — игнорируем сообщение.
MIN_CONFIDENCE = 0.5


def _ranges_overlap(a_lo: int, a_hi: int, b_lo: int, b_hi: int) -> bool:
    return not (a_hi < b_lo or a_lo > b_hi)


def _intersect(a: Iterable[str], b: Iterable[str]) -> bool:
    return bool(set(a) & set(b))


def matches(profile: CreativeProfile, post: PostExtraction, vacancy: VacancyExtraction) -> bool:
    """True, если анкета подходит под конкретную вакансию в этом посте.

    project_types и city берём с уровня поста (общие);
    gender / age / role_types / rate — с уровня вакансии.
    Если параметр не указан в объявлении — фильтр по нему не применяется.
    """
    # Пол (per-vacancy)
    if vacancy.gender and profile.gender and vacancy.gender != profile.gender:
        return False

    # Возраст (per-vacancy)
    if vacancy.age_min is not None or vacancy.age_max is not None:
        msg_lo = vacancy.age_min if vacancy.age_min is not None else 0
        msg_hi = vacancy.age_max if vacancy.age_max is not None else 120
        prof_lo = profile.play_age_min if profile.play_age_min is not None else 0
        prof_hi = profile.play_age_max if profile.play_age_max is not None else 120
        if not _ranges_overlap(msg_lo, msg_hi, prof_lo, prof_hi):
            return False

    # Типы проектов (post-level)
    if post.project_types and profile.project_types:
        if not _intersect(post.project_types, profile.project_types):
            return False

    # Типы ролей (per-vacancy)
    if vacancy.role_types and profile.role_types:
        if not _intersect(vacancy.role_types, profile.role_types):
            return False

    # Ставка (per-vacancy)
    if vacancy.rate is not None and profile.min_rate is not None and vacancy.rate < profile.min_rate:
        return False

    # Этническая внешность (per-vacancy): если в вакансии указан список —
    # анкета должна подходить хотя бы под один из перечисленных типов.
    # Если у профиля этнос не задан — пропускаем (нет основания фильтровать).
    if vacancy.ethnicity and profile.ethnicity:
        if not _intersect(vacancy.ethnicity, profile.ethnicity):
            return False

    # Рост (per-vacancy): если у вакансии указан диапазон — рост из профиля
    # должен в него попасть. Если в профиле height_cm не задан — пропускаем.
    if (vacancy.height_min is not None or vacancy.height_max is not None) and profile.height_cm is not None:
        v_lo = vacancy.height_min if vacancy.height_min is not None else 0
        v_hi = vacancy.height_max if vacancy.height_max is not None else 999
        if not (v_lo <= profile.height_cm <= v_hi):
            return False

    # Телосложение (per-vacancy)
    if vacancy.body_type and profile.body_type:
        if not _intersect(vacancy.body_type, profile.body_type):
            return False

    # Цвет волос (per-vacancy): в профиле один цвет, в вакансии может быть
    # список разрешённых. Если в профиле не задан — пропускаем.
    if vacancy.hair_color and profile.hair_color:
        if profile.hair_color not in vacancy.hair_color:
            return False

    # Длина волос (per-vacancy): аналогично цвету.
    if vacancy.hair_length and profile.hair_length:
        if profile.hair_length not in vacancy.hair_length:
            return False

    # Город (post-level), с поправкой на ready_for_travel
    if post.city and profile.city:
        if post.city.lower() != profile.city.lower() and not profile.ready_for_travel:
            return False

    return True


async def find_matching_vacancies(
    post: PostExtraction,
    vacancies: list[VacancyExtraction],
) -> dict[int, list[int]]:
    """Возвращает {user_id: [индексы подошедших вакансий в списке `vacancies`]}.

    Гейтим по is_casting/confidence на уровне поста.
    Учитываем только анкеты creative-категории с completed_at IS NOT NULL,
    у которых подписка включена (UserCategorySubscription.enabled=TRUE).
    Индексы соответствуют позициям в `vacancies`, что 1-в-1 совпадает с idx
    в БД, потому что Vacancy сохраняется с idx=enumerate(vacancies).
    """
    if not post.is_casting or post.confidence < MIN_CONFIDENCE or not vacancies:
        return {}

    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(CreativeProfile)
            .join(
                UserCategorySubscription,
                UserCategorySubscription.user_id == CreativeProfile.user_id,
            )
            .where(
                CreativeProfile.completed_at.is_not(None),
                UserCategorySubscription.category == "creative",
                UserCategorySubscription.enabled.is_(True),
            )
        )
        profiles = res.scalars().all()

    out: dict[int, list[int]] = {}
    for p in profiles:
        hit_idxs = [i for i, v in enumerate(vacancies) if matches(p, post, v)]
        if hit_idxs:
            out[p.user_id] = hit_idxs
    return out


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
        category=message.category,
        project_types=list(message.project_types),
        city=message.city,
        summary=message.summary,
        confidence=message.confidence,
        vacancies=[],
    )
    vac_extractions = [
        VacancyExtraction(
            role_types=list(v.role_types),
            work_types=list(v.work_types or []),
            category=v.category,
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
