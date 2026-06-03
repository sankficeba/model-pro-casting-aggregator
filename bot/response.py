"""Сборка текста отклика на вакансию по данным per-category профиля."""
from __future__ import annotations

from api.reference_data import all_refs
from db.repository import ResponseProfile

_REFS = all_refs()
_SKILL_LABELS: dict[str, str] = {}
for _key in ("skills_sport", "skills_dance", "skills_vocal", "skills_instruments"):
    for _it in _REFS[_key]:
        _SKILL_LABELS[_it["code"]] = _it["label"]

_WORK_TYPE_LABELS: dict[str, str] = {}
for _key in ("work_types_event", "work_types_general", "work_types_admin"):
    for _it in _REFS[_key]:
        _WORK_TYPE_LABELS[_it["code"]] = _it["label"]


def compose_response(rp: ResponseProfile, role_label: str) -> str:
    """Формирует текст отклика в структурированном формате.

    Формат:
        Откликаюсь: <роль>
        ФИО: <имя>
        Возраст: <возраст>
        Телефон: <телефон>
        Рост / размеры: X / Y  (только creative и event)
        Опыт: <текст опыта>
    """
    lines: list[str] = []

    lines.append(f"Откликаюсь: {role_label}")
    lines.append(f"ФИО: {rp.full_name or '—'}")
    if rp.actual_age is not None:
        lines.append(f"Возраст: {rp.actual_age}")
    lines.append(f"Телефон: {rp.phone or '—'}")

    if rp.category in ("creative", "event"):
        size_parts: list[str] = []
        if rp.height_cm:
            size_parts.append(str(rp.height_cm))
        if rp.clothing_size:
            size_parts.append(str(rp.clothing_size))
        if size_parts:
            lines.append(f"Рост / размеры: {' / '.join(size_parts)}")

    if rp.experience_text:
        lines.append(f"Опыт: {rp.experience_text}")
    elif rp.category == "creative":
        skill_labels: list[str] = []
        for code in rp.skills_sport + rp.skills_dance + rp.skills_vocal + rp.skills_instruments:
            lbl = _SKILL_LABELS.get(code, code)
            skill_labels.append(lbl)
        if skill_labels:
            lines.append(f"Навыки: {', '.join(skill_labels)}")
        elif rp.has_experience is True:
            lines.append("Опыт съёмок: есть")
        elif rp.has_experience is False:
            lines.append("Опыт съёмок: пока нет")

    return "\n".join(lines)
