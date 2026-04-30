"""Шаблон автоматического отклика на вакансию.

Берём данные из анкеты пользователя + контекст вакансии и собираем готовый
текст, который пользователь может скопировать и отправить кастинг-директору.
Никаких LLM-вызовов — детерминированный шаблон.
"""
from __future__ import annotations

from api.reference_data import all_refs
from api.schemas import ProfileResponse
from db.models import Message, Vacancy

_REFS = all_refs()
_PROJECT_LABELS = {it["code"]: it["label"] for it in _REFS["project_types"]}
_ROLE_LABELS = {it["code"]: it["label"] for it in _REFS["role_types"]}
_ETHNICITY_LABELS = {it["code"]: it["label"] for it in _REFS["ethnicity"]}
_BODY_TYPE_LABELS = {it["code"]: it["label"] for it in _REFS["body_type"]}
_HAIR_COLOR_LABELS = {it["code"]: it["label"] for it in _REFS["hair_colors"]}


def _label(codes: list[str], mapping: dict[str, str]) -> str:
    if not codes:
        return ""
    return ", ".join(mapping.get(c, c) for c in codes)


def _vacancy_title(v: Vacancy) -> str:
    if v.role_label:
        return v.role_label
    if v.role_types:
        return _ROLE_LABELS.get(v.role_types[0], v.role_types[0])
    return "роль"


def compose_response(
    profile: ProfileResponse, message: Message, vacancy: Vacancy
) -> str:
    """Собирает текст отклика. Возвращает plain-text без HTML-тегов
    (бот сам обернёт в <code>…</code> для удобного копирования)."""
    role = _vacancy_title(vacancy)
    project = _label(list(message.project_types or []), _PROJECT_LABELS)
    project_phrase = f" в проекте «{project}»" if project else ""

    name = profile.full_name or "—"
    gender_ru = {"male": "мужчина", "female": "женщина"}.get(profile.gender or "", "")
    age = profile.actual_age
    play_age = ""
    if profile.play_age_min is not None and profile.play_age_max is not None:
        if profile.play_age_min == profile.play_age_max:
            play_age = f" (играю {profile.play_age_min})"
        else:
            play_age = f" (играю {profile.play_age_min}–{profile.play_age_max})"

    intro_bits: list[str] = []
    if name != "—":
        intro_bits.append(f"Меня зовут {name}.")
    person_bits: list[str] = []
    if gender_ru:
        person_bits.append(gender_ru)
    if age is not None:
        person_bits.append(f"{age} лет{play_age}")
    if person_bits:
        intro_bits.append(", ".join(person_bits) + ".")

    location_bits: list[str] = []
    if profile.city:
        city_line = f"Город: {profile.city}"
        if profile.ready_for_travel:
            city_line += " (готов(а) к командировкам)"
        location_bits.append(city_line)

    physical: list[str] = []
    if profile.height_cm:
        physical.append(f"рост {profile.height_cm} см")
    body_lbl = _label(list(profile.body_type or []), _BODY_TYPE_LABELS)
    if body_lbl:
        physical.append(f"телосложение: {body_lbl.lower()}")
    eth_lbl = _label(list(profile.ethnicity or []), _ETHNICITY_LABELS)
    if eth_lbl:
        physical.append(f"внешность: {eth_lbl.lower()}")
    if profile.hair_color:
        hc = _HAIR_COLOR_LABELS.get(profile.hair_color, profile.hair_color)
        physical.append(f"волосы: {hc.lower()}")

    experience_line = ""
    if profile.has_experience is True:
        experience_line = "Опыт съёмок есть."
    elif profile.has_experience is False:
        experience_line = "Опыта съёмок пока нет, но открыт(а) к новому."

    contacts: list[str] = []
    if profile.phone:
        contacts.append(f"телефон: {profile.phone}")
    if profile.email:
        contacts.append(f"email: {profile.email}")
    if profile.vk_url:
        contacts.append(f"ВК: {profile.vk_url}")
    media: list[str] = []
    if profile.portfolio_url:
        media.append(f"портфолио: {profile.portfolio_url}")
    if profile.video_url:
        media.append(f"визитка: {profile.video_url}")
    if profile.professional_url:
        media.append(f"проф. ссылка: {profile.professional_url}")

    lines: list[str] = []
    lines.append(
        f"Здравствуйте! Откликаюсь на роль «{role}»{project_phrase}."
    )
    lines.append("")
    lines.extend(intro_bits)
    lines.extend(location_bits)
    if physical:
        lines.append("Параметры: " + ", ".join(physical) + ".")
    if experience_line:
        lines.append(experience_line)

    if contacts or media:
        lines.append("")
        lines.append("Контакты:")
        for c in contacts:
            lines.append(f"• {c}")
        for m in media:
            lines.append(f"• {m}")

    lines.append("")
    lines.append("Готов(а) обсудить условия, пробы, расписание.")

    return "\n".join(lines)
