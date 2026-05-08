"""Постобработка LLM-extract: подменяем русские лейблы и опечатки на
канонические коды из api/reference_data.py.

Зачем: gpt-4o-mini периодически возвращает в project_types/role_types
лейбл вместо кода ("реклама" вместо "advertising"). Из-за этого сравнение
set'ов в db.matching ничего не находит, и пользователь не получает
уведомление. Нормализуем, чтобы матчинг работал даже при таких ошибках.
"""
from __future__ import annotations

from api.reference_data import all_refs
from models.schemas import PostExtraction, VacancyExtraction


def _build_indexes() -> tuple[dict[str, set[str]], dict[str, dict[str, str]]]:
    """Возвращает:
    - codes_by_category: {category: set_of_valid_codes}
    - label_to_code_by_category: {category: {label_lowercase: code}}
    """
    refs = all_refs()
    codes_by: dict[str, set[str]] = {}
    label_to_code_by: dict[str, dict[str, str]] = {}
    for category, items in refs.items():
        codes_by[category] = {it["code"] for it in items}
        label_to_code_by[category] = {it["label"].lower(): it["code"] for it in items}
    return codes_by, label_to_code_by


_CODES, _LABELS = _build_indexes()


def _normalize_one(category: str, raw: str) -> str | None:
    valid = _CODES.get(category, set())
    label_map = _LABELS.get(category, {})
    s = (raw or "").strip()
    if not s:
        return None
    if s in valid:
        return s
    code = label_map.get(s.lower())
    if code:
        return code
    cleaned = s.lower().replace("-", " ").replace("_", " ").strip()
    return label_map.get(cleaned)


def _normalize_list(category: str, raw: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for x in raw or []:
        norm = _normalize_one(category, x)
        if norm is not None and norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


def _normalize_vacancy(v: VacancyExtraction) -> VacancyExtraction:
    # work_types: справочник зависит от категории. Если категория не задана
    # на уровне вакансии (типичный случай) — нормализовать по объединению
    # всех трёх whitelist'ов; если LLM вернул мусор, он отфильтруется
    # на следующем уровне (per-category matcher).
    work_types_normalized = (
        _normalize_list("work_types_event", v.work_types)
        + _normalize_list("work_types_general", v.work_types)
        + _normalize_list("work_types_admin", v.work_types)
    )
    # Дедупликация
    seen: set[str] = set()
    work_types_dedup: list[str] = []
    for code in work_types_normalized:
        if code not in seen:
            seen.add(code)
            work_types_dedup.append(code)

    return v.model_copy(
        update={
            "role_types": _normalize_list("role_types", v.role_types),
            "work_types": work_types_dedup,
            "ethnicity": _normalize_list("ethnicity", v.ethnicity),
            "body_type": _normalize_list("body_type", v.body_type),
            "hair_color": _normalize_list("hair_colors", v.hair_color),
            "hair_length": _normalize_list("hair_lengths", v.hair_length),
        }
    )


def normalize_extracted(data: PostExtraction) -> PostExtraction:
    """Возвращает копию PostExtraction с нормализованными списками кодов
    на уровне поста (project_types) и каждой вакансии (role_types)."""
    return data.model_copy(
        update={
            "project_types": _normalize_list("project_types", data.project_types),
            "vacancies": [_normalize_vacancy(v) for v in data.vacancies],
        }
    )
