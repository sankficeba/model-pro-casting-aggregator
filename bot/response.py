"""Сборка автоматического отклика на вакансию.

Два режима:
- compose_response — детерминированный шаблон без LLM. Гарантированный
  fallback, не тратит токены.
- compose_response_llm — даёт LLM собрать «живой» текст под конкретную
  вакансию. На любую ошибку откатывается на шаблон.
"""
from __future__ import annotations

import json

from loguru import logger

from api.reference_data import all_refs
from api.schemas import ProfileResponse
from db.models import Message, Vacancy
from llm.base import LLMProvider, _try_parse_json

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


# ---------- LLM-режим ----------

_RESPONSE_SYSTEM_PROMPT = """Ты помогаешь актёру/модели написать короткий
персональный отклик на конкретную вакансию из объявления о кастинге.

Правила:
- Текст на русском, тон — вежливый, дружелюбный, профессиональный, без
  излишнего пафоса и канцелярита.
- 5–10 коротких строк. Без эмодзи. Без заголовков. Без markdown.
- Опирайся ТОЛЬКО на данные анкеты и описание вакансии. Не выдумывай
  опыт, награды, навыки, города или факты.
- Подчеркни, чем кандидат подходит именно под эту роль (роль, возраст,
  пол, рост, внешность, телосложение — если они совпадают с требованием).
- Контакты приведи в конце отдельным блоком, по одному на строке.
  Никаких кликабельных ссылок-приукрас, плоский текст.
- Если каких-то данных в анкете нет — просто опусти соответствующую
  фразу, не пиши «не указано», «—» и т.п.
- Заверши готовностью обсудить пробы/условия.

Ответ — СТРОГО JSON-объект без markdown:
{"text": "<готовый текст отклика, переносы строк через \\n>"}
"""


def _profile_to_dict(p: ProfileResponse) -> dict:
    """Сериализация анкеты для LLM — только осмысленные для отклика поля."""
    refs = _REFS
    proj_lbl = {it["code"]: it["label"] for it in refs["project_types"]}
    role_lbl = {it["code"]: it["label"] for it in refs["role_types"]}
    eth_lbl = {it["code"]: it["label"] for it in refs["ethnicity"]}
    body_lbl = {it["code"]: it["label"] for it in refs["body_type"]}
    hair_lbl = {it["code"]: it["label"] for it in refs["hair_colors"]}
    hair_len_lbl = {it["code"]: it["label"] for it in refs["hair_lengths"]}

    return {
        "full_name": p.full_name,
        "gender": p.gender,
        "city": p.city,
        "ready_for_travel": p.ready_for_travel,
        "actual_age": p.actual_age,
        "play_age": (
            f"{p.play_age_min}–{p.play_age_max}"
            if p.play_age_min is not None and p.play_age_max is not None
            else None
        ),
        "project_types": [proj_lbl.get(c, c) for c in (p.project_types or [])],
        "role_types": [role_lbl.get(c, c) for c in (p.role_types or [])],
        "height_cm": p.height_cm,
        "ethnicity": [eth_lbl.get(c, c) for c in (p.ethnicity or [])],
        "body_type": [body_lbl.get(c, c) for c in (p.body_type or [])],
        "hair_color": hair_lbl.get(p.hair_color, p.hair_color) if p.hair_color else None,
        "hair_length": hair_len_lbl.get(p.hair_length, p.hair_length) if p.hair_length else None,
        "has_experience": p.has_experience,
        "phone": p.phone,
        "email": p.email,
        "vk_url": p.vk_url,
        "portfolio_url": p.portfolio_url,
        "video_url": p.video_url,
        "professional_url": p.professional_url,
    }


def _vacancy_to_dict(message: Message, vacancy: Vacancy) -> dict:
    """Сериализация вакансии + контекста поста для LLM."""
    eth_lbl = {it["code"]: it["label"] for it in _REFS["ethnicity"]}
    body_lbl = {it["code"]: it["label"] for it in _REFS["body_type"]}
    hair_lbl = {it["code"]: it["label"] for it in _REFS["hair_colors"]}
    hair_len_lbl = {it["code"]: it["label"] for it in _REFS["hair_lengths"]}

    return {
        "role_label": vacancy.role_label,
        "role_types": [_ROLE_LABELS.get(c, c) for c in (vacancy.role_types or [])],
        "gender": vacancy.gender,
        "age_min": vacancy.age_min,
        "age_max": vacancy.age_max,
        "rate": vacancy.rate,
        "ethnicity": [eth_lbl.get(c, c) for c in (vacancy.ethnicity or [])],
        "height_min": vacancy.height_min,
        "height_max": vacancy.height_max,
        "body_type": [body_lbl.get(c, c) for c in (vacancy.body_type or [])],
        "hair_color": [hair_lbl.get(c, c) for c in (vacancy.hair_color or [])],
        "hair_length": [hair_len_lbl.get(c, c) for c in (vacancy.hair_length or [])],
        "description": vacancy.description,
        "project_types": [_PROJECT_LABELS.get(c, c) for c in (message.project_types or [])],
        "city": message.city,
        "summary": message.summary,
    }


async def compose_response_llm(
    profile: ProfileResponse,
    message: Message,
    vacancy: Vacancy,
    llm: LLMProvider,
) -> str:
    """LLM-вариант. На любую ошибку откатывается на шаблон compose_response."""
    user_payload = {
        "candidate": _profile_to_dict(profile),
        "vacancy": _vacancy_to_dict(message, vacancy),
    }
    try:
        raw = await llm._complete_json(
            _RESPONSE_SYSTEM_PROMPT,
            json.dumps(user_payload, ensure_ascii=False),
        )
        data = _try_parse_json(raw)
        text = (data.get("text") or "").strip()
        if not text:
            raise ValueError("LLM вернул пустой text")
        return text
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "compose_response_llm fallback to template (vacancy_id={}): {}",
            vacancy.id, e,
        )
        return compose_response(profile, message, vacancy)
