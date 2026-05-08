"""Сопоставление извлечённого объявления с анкетами пользователей.

Per-category архитектура: для каждой категории (creative/event/general/admin)
своя функция `_check_<cat>_match` с правилами + загрузка соответствующей
профиль-таблицы. Диспатчер `find_matching_vacancies` определяет
effective_cat по vacancy.category или post.category и вызывает нужный matcher.
"""
from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import select

from db.models import (
    AdminProfile,
    CreativeProfile,
    EventProfile,
    GeneralProfile,
    Message,
    UserCategorySubscription,
    Vacancy,
)
from db.session import AsyncSessionLocal
from models.schemas import PostExtraction, VacancyExtraction

# Минимальная уверенность LLM для рассылки. Ниже — игнорируем сообщение.
MIN_CONFIDENCE = 0.5


# ============================================================================
# Низкоуровневые помощники
# ============================================================================


def _ranges_overlap(a_lo: int, a_hi: int, b_lo: int, b_hi: int) -> bool:
    return not (a_hi < b_lo or a_lo > b_hi)


def _intersect(a: Iterable[str], b: Iterable[str]) -> bool:
    return bool(set(a) & set(b))


def _city_ok(post_city: Optional[str], profile_city: Optional[str], travel: bool) -> bool:
    """Город матчится либо когда совпадает, либо когда юзер готов к разъездам.
    Если в посте город не указан или у юзера нет — фильтр не применяется."""
    if not post_city or not profile_city:
        return True
    if post_city.lower() == profile_city.lower():
        return True
    return travel


def _gender_ok(vacancy_gender: Optional[str], profile_gender: Optional[str]) -> bool:
    """Если в вакансии указан конкретный пол — должен совпадать с профилем."""
    if not vacancy_gender:
        return True
    if not profile_gender:
        return True
    return vacancy_gender == profile_gender


def _rate_ok(vacancy_rate: Optional[int], profile_min_rate: Optional[int]) -> bool:
    """Ставка вакансии должна быть >= минимальной ставки юзера, если оба указаны."""
    if vacancy_rate is None or profile_min_rate is None:
        return True
    return vacancy_rate >= profile_min_rate


def _age_overlaps(
    vacancy_min: Optional[int],
    vacancy_max: Optional[int],
    profile_min: Optional[int],
    profile_max: Optional[int],
) -> bool:
    """Диапазон возраста вакансии пересекается с возрастом профиля.
    Если у вакансии нет возрастных требований — пропускаем."""
    if vacancy_min is None and vacancy_max is None:
        return True
    v_lo = vacancy_min if vacancy_min is not None else 0
    v_hi = vacancy_max if vacancy_max is not None else 120
    p_lo = profile_min if profile_min is not None else 0
    p_hi = profile_max if profile_max is not None else 120
    return _ranges_overlap(v_lo, v_hi, p_lo, p_hi)


def _height_ok(vacancy_min: Optional[int], vacancy_max: Optional[int], profile_height: Optional[int]) -> bool:
    if vacancy_min is None and vacancy_max is None:
        return True
    if profile_height is None:
        return True  # в профиле не указан — не фильтруем
    v_lo = vacancy_min if vacancy_min is not None else 0
    v_hi = vacancy_max if vacancy_max is not None else 999
    return v_lo <= profile_height <= v_hi


# ============================================================================
# Per-category matchers
# ============================================================================


def _check_creative_match(profile: CreativeProfile, post: PostExtraction, vacancy: VacancyExtraction) -> bool:
    """True, если creative-профиль подходит под вакансию.

    Использует play_age_min/max (играемый возраст). Учитывает project_types
    (post-level) и role_types (per-vacancy). Все физические параметры
    опциональны — фильтруются только если LLM их извлёк."""
    if not _gender_ok(vacancy.gender, profile.gender):
        return False
    if not _age_overlaps(vacancy.age_min, vacancy.age_max, profile.play_age_min, profile.play_age_max):
        return False
    if post.project_types and profile.project_types:
        if not _intersect(post.project_types, profile.project_types):
            return False
    if vacancy.role_types and profile.role_types:
        if not _intersect(vacancy.role_types, profile.role_types):
            return False
    if not _rate_ok(vacancy.rate, profile.min_rate):
        return False
    if vacancy.ethnicity and profile.ethnicity:
        if not _intersect(vacancy.ethnicity, profile.ethnicity):
            return False
    if not _height_ok(vacancy.height_min, vacancy.height_max, profile.height_cm):
        return False
    if vacancy.body_type and profile.body_type:
        if not _intersect(vacancy.body_type, profile.body_type):
            return False
    if vacancy.hair_color and profile.hair_color:
        if profile.hair_color not in vacancy.hair_color:
            return False
    if vacancy.hair_length and profile.hair_length:
        if profile.hair_length not in vacancy.hair_length:
            return False
    if not _city_ok(post.city, profile.city, profile.ready_for_travel):
        return False
    return True


def _check_event_match(profile: EventProfile, post: PostExtraction, vacancy: VacancyExtraction) -> bool:
    """True, если event-профиль подходит под вакансию.

    Использует actual_age (актуальный, single value). Обязательная проверка
    work_types (если в вакансии указаны). Физические параметры опциональны."""
    if vacancy.work_types and profile.work_types:
        if not _intersect(vacancy.work_types, profile.work_types):
            return False
    if not _gender_ok(vacancy.gender, profile.gender):
        return False
    if not _age_overlaps(vacancy.age_min, vacancy.age_max, profile.actual_age, profile.actual_age):
        return False
    if not _rate_ok(vacancy.rate, profile.min_rate):
        return False
    if vacancy.ethnicity and profile.ethnicity:
        if not _intersect(vacancy.ethnicity, profile.ethnicity):
            return False
    if not _height_ok(vacancy.height_min, vacancy.height_max, profile.height_cm):
        return False
    if vacancy.body_type and profile.body_type:
        if not _intersect(vacancy.body_type, profile.body_type):
            return False
    if vacancy.hair_color and profile.hair_color:
        if profile.hair_color not in vacancy.hair_color:
            return False
    if vacancy.hair_length and profile.hair_length:
        if profile.hair_length not in vacancy.hair_length:
            return False
    if not _city_ok(post.city, profile.city, profile.ready_for_travel):
        return False
    return True


def _check_general_match(profile: GeneralProfile, post: PostExtraction, vacancy: VacancyExtraction) -> bool:
    """True, если general-профиль подходит под вакансию.

    Только work_types + actual_age + gender + rate + city.
    physical_fitness НЕ матчится (поле осталось для UI/будущего)."""
    if vacancy.work_types and profile.work_types:
        if not _intersect(vacancy.work_types, profile.work_types):
            return False
    if not _gender_ok(vacancy.gender, profile.gender):
        return False
    if not _age_overlaps(vacancy.age_min, vacancy.age_max, profile.actual_age, profile.actual_age):
        return False
    if not _rate_ok(vacancy.rate, profile.min_rate):
        return False
    if not _city_ok(post.city, profile.city, profile.ready_for_travel):
        return False
    return True


def _check_admin_match(profile: AdminProfile, post: PostExtraction, vacancy: VacancyExtraction) -> bool:
    """True, если admin-профиль подходит под вакансию.

    Только work_types + actual_age + rate + city.
    gender и education НЕ матчятся (gender обычно не указывается, education
    оставлено в UI для будущего)."""
    if vacancy.work_types and profile.work_types:
        if not _intersect(vacancy.work_types, profile.work_types):
            return False
    if not _age_overlaps(vacancy.age_min, vacancy.age_max, profile.actual_age, profile.actual_age):
        return False
    if not _rate_ok(vacancy.rate, profile.min_rate):
        return False
    if not _city_ok(post.city, profile.city, profile.ready_for_travel):
        return False
    return True


# ============================================================================
# Диспатчер
# ============================================================================


def _resolve_effective_category(
    post: PostExtraction, vacancy: VacancyExtraction
) -> Optional[str]:
    """Resolve effective category: vacancy.category overrides post.category."""
    return vacancy.category or post.category


async def _load_profiles_for_category(category: str) -> list:
    """Загружает профили нужной таблицы с фильтром по UserCategorySubscription."""
    profile_classes = {
        "creative": CreativeProfile,
        "event": EventProfile,
        "general": GeneralProfile,
        "admin": AdminProfile,
    }
    Profile = profile_classes[category]
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Profile)
            .join(
                UserCategorySubscription,
                UserCategorySubscription.user_id == Profile.user_id,
            )
            .where(
                Profile.completed_at.is_not(None),
                UserCategorySubscription.category == category,
                UserCategorySubscription.enabled.is_(True),
            )
        )
        return list(res.scalars().all())


_CATEGORY_MATCHERS = {
    "creative": _check_creative_match,
    "event": _check_event_match,
    "general": _check_general_match,
    "admin": _check_admin_match,
}


async def find_matching_vacancies(
    post: PostExtraction,
    vacancies: list[VacancyExtraction],
) -> dict[int, list[int]]:
    """Возвращает {user_id: [индексы подошедших вакансий в списке `vacancies`]}.

    Гейтит по is_casting/confidence на уровне поста.
    Для каждой вакансии resolve effective_category (vacancy.category or
    post.category), загружает соответствующую профиль-таблицу и проверяет
    per-category matcher.
    """
    if not post.is_casting or post.confidence < MIN_CONFIDENCE or not vacancies:
        return {}

    # Кэш загруженных профилей по категории — чтобы не грузить дважды,
    # если в посте несколько вакансий одной категории.
    profiles_cache: dict[str, list] = {}
    out: dict[int, list[int]] = {}

    for idx, v in enumerate(vacancies):
        eff_cat = _resolve_effective_category(post, v)
        if eff_cat is None:
            continue
        matcher = _CATEGORY_MATCHERS.get(eff_cat)
        if matcher is None:
            continue
        if eff_cat not in profiles_cache:
            profiles_cache[eff_cat] = await _load_profiles_for_category(eff_cat)
        for profile in profiles_cache[eff_cat]:
            if matcher(profile, post, v):
                out.setdefault(profile.user_id, []).append(idx)
    return out


# ============================================================================
# ORM → Pydantic конвертер (используется в duplicate-пути userbot._handle_message)
# ============================================================================


def _orm_to_extractions(
    message: Message,
    vacancies: list[Vacancy],
) -> tuple[PostExtraction, list[VacancyExtraction]]:
    """Конвертер ORM Message + Vacancy → Pydantic PostExtraction +
    VacancyExtraction.

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
