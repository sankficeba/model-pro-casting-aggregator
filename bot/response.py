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


def compose_response(
    rp: ResponseProfile,
    role_label: str,
    message_link: str | None = None,
) -> str:
    """Формирует текст отклика.

    Формат:
        Здравствуйте, откликаюсь на <роль>
        <ссылка на сообщение>

        <ФИО>
        <возраст>
        <телефон>
        <рост> / <размер>   (только creative и event)
        <текст опыта>
    """
    lines: list[str] = []

    lines.append(f"Здравствуйте, откликаюсь на {role_label}")
    if message_link:
        lines.append(message_link)
    lines.append("")

    if rp.full_name:
        lines.append(rp.full_name)
    if rp.actual_age is not None:
        lines.append(str(rp.actual_age))
    if rp.phone:
        lines.append(rp.phone)

    if rp.category in ("creative", "event"):
        size_parts: list[str] = []
        if rp.height_cm:
            size_parts.append(str(rp.height_cm))
        if rp.clothing_size:
            size_parts.append(str(rp.clothing_size))
        if size_parts:
            lines.append(" / ".join(size_parts))

    if rp.experience_text:
        lines.append(rp.experience_text)
    elif rp.category == "creative":
        skill_labels: list[str] = []
        for code in rp.skills_sport + rp.skills_dance + rp.skills_vocal + rp.skills_instruments:
            skill_labels.append(_SKILL_LABELS.get(code, code))
        if skill_labels:
            lines.append(", ".join(skill_labels))
        elif rp.has_experience is True:
            lines.append("Опыт съёмок есть")
        elif rp.has_experience is False:
            lines.append("Опыта съёмок пока нет")

    return "\n".join(lines)
