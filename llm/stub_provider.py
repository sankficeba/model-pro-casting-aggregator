"""Заглушка LLM: без внешних API, парсит сообщение по простым правилам.
Нужна, чтобы тестировать пайплайн end-to-end, пока нет реального LLM-ключа."""
from __future__ import annotations

import re

from loguru import logger

from llm.base import LLMProvider, _try_parse_json  # noqa: F401  # переиспользуем не нужно
from models.schemas import ExtractedData


# Ключевые слова для пола (русский + английский)
_MALE_WORDS = {
    "мужчина", "мужчины", "парень", "парня", "парни", "мальчик", "юноша",
    "мужской", "мужского", "сын", "муж", "male", "man", "boy", "guy",
}
_FEMALE_WORDS = {
    "женщина", "женщины", "девушка", "девушку", "девушки", "девочка", "дама",
    "женский", "женского", "дочь", "жена", "female", "woman", "girl", "lady",
}

# Категории по ключевым словам (фрагменты подстрок)
_CATEGORY_PATTERNS = [
    ("обучение", ["обучен", "курс", "урок", "репетит", "школа", "тренинг", "lesson", "course"]),
    ("работа", ["работа", "вакансия", "ищу сотрудник", "наём", "hiring", "job", "вакан"]),
    ("аренда", ["аренда", "сниму", "сдаю", "сдается", "сдаётся", "rent"]),
    ("покупка", ["куплю", "продам", "продаю", "покупка", "продажа", "buy", "sell"]),
    ("услуга", ["услуг", "service"]),
]


def _detect_gender(text: str) -> str | None:
    words = set(re.findall(r"\b\w+\b", text.lower()))
    if words & _MALE_WORDS:
        return "male"
    if words & _FEMALE_WORDS:
        return "female"
    return None


def _detect_age(text: str) -> int | None:
    # Сначала пробуем «25 лет», «35-летний», «возраст 30»
    m = re.search(r"\b(\d{1,2})\s*(?:лет|года|год|y\.?o\.?|years?)\b", text, re.IGNORECASE)
    if m:
        age = int(m.group(1))
        if 5 <= age <= 100:
            return age
    m = re.search(r"возраст[:\s]+(\d{1,2})", text, re.IGNORECASE)
    if m:
        age = int(m.group(1))
        if 5 <= age <= 100:
            return age
    return None


def _detect_category(text: str) -> str | None:
    low = text.lower()
    for cat, patterns in _CATEGORY_PATTERNS:
        if any(p in low for p in patterns):
            return cat
    return None


class StubProvider(LLMProvider):
    """Эмулирует LLM regex-эвристиками. Никаких внешних запросов."""

    async def _complete_json(self, system: str, user: str) -> str:  # noqa: ARG002
        # Не используется — мы переопределяем extract напрямую
        return "{}"

    async def extract(self, text: str) -> ExtractedData:
        gender = _detect_gender(text)
        age = _detect_age(text)
        category = _detect_category(text)
        summary = text.strip().replace("\n", " ")[:120]

        # Уверенность зависит от количества распознанных полей.
        hits = sum(x is not None for x in (gender, age, category))
        # Базовая уверенность 0.5, чтобы сообщения с дефолтным min_confidence=0.5 проходили
        confidence = min(1.0, 0.5 + 0.15 * hits)

        result = ExtractedData(
            gender=gender,
            age=age,
            category=category,
            summary=summary or None,
            confidence=confidence,
        )
        logger.debug("StubProvider extracted: {}", result.model_dump())
        return result
