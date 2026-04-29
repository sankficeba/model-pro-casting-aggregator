"""Заглушка LLM: без внешних API, грубое извлечение по ключевым словам.
Эмулирует один-вакансия-на-пост (мульти-вакансия для regex-стаба нереалистична).
"""
from __future__ import annotations

import re

from loguru import logger

from llm.base import LLMProvider
from models.schemas import PostExtraction, VacancyExtraction

_MALE_WORDS = {
    "мужчина", "мужчины", "парень", "парни", "юноша", "мужской",
    "male", "man", "boy",
}
_FEMALE_WORDS = {
    "женщина", "девушка", "девочка", "женский", "дама",
    "female", "woman", "girl",
}
_CASTING_HINTS = (
    "кастинг", "съёмк", "съемк", "роль", "актёр", "актер", "актрис",
    "модел", "проект", "клип", "сериал", "реклам",
)


def _detect_gender(text: str) -> str | None:
    words = set(re.findall(r"\b\w+\b", text.lower()))
    if words & _MALE_WORDS:
        return "male"
    if words & _FEMALE_WORDS:
        return "female"
    return None


def _detect_age_range(text: str) -> tuple[int | None, int | None]:
    # Сначала диапазон: "18-30", "20–35", "от 25 до 40"
    m = re.search(r"(\d{1,2})\s*[-–—]\s*(\d{1,2})", text)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        if 5 <= lo <= 100 and 5 <= hi <= 100 and lo <= hi:
            return lo, hi
    m = re.search(r"от\s+(\d{1,2})\s+до\s+(\d{1,2})", text, re.IGNORECASE)
    if m:
        return int(m.group(1)), int(m.group(2))
    # Одиночный возраст
    m = re.search(r"\b(\d{1,2})\s*(?:лет|года|год)\b", text, re.IGNORECASE)
    if m:
        age = int(m.group(1))
        if 5 <= age <= 100:
            return age, age
    return None, None


class StubProvider(LLMProvider):
    """Эмулирует LLM regex-эвристиками. Никаких внешних запросов."""

    async def _complete_json(self, system: str, user: str) -> str:  # noqa: ARG002
        return "{}"

    async def extract(self, text: str) -> PostExtraction:
        low = text.lower()
        is_casting = any(h in low for h in _CASTING_HINTS)
        gender = _detect_gender(text)
        age_min, age_max = _detect_age_range(text)
        summary = text.strip().replace("\n", " ")[:160]

        hits = sum(x is not None for x in (gender, age_min)) + (1 if is_casting else 0)
        confidence = min(1.0, 0.4 + 0.15 * hits)

        vacancies: list[VacancyExtraction] = []
        if is_casting:
            vacancies = [
                VacancyExtraction(
                    gender=gender,  # type: ignore[arg-type]
                    age_min=age_min,
                    age_max=age_max,
                    description=summary or None,
                ),
            ]

        result = PostExtraction(
            is_casting=is_casting,
            summary=summary or None,
            confidence=confidence,
            vacancies=vacancies,
        )
        logger.debug("StubProvider extracted: {}", result.model_dump())
        return result
