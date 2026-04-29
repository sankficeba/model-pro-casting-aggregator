"""Абстрактный интерфейс LLM-провайдера."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger
from pydantic import ValidationError

from llm.normalize import normalize_extracted
from models.schemas import ExtractedData

SYSTEM_PROMPT = """Ты разбираешь объявления о кастингах на актёров и моделей
из Telegram-каналов. Из присланного сообщения нужно извлечь параметры
поиска и вернуть СТРОГО JSON-объект без markdown-обёрток.

Ключи (если параметра нет — ставь null или []):
- is_casting (bool): это объявление о кастинге/съёмке/ролях/моделях?
  false — для рекламы услуг, обучения, частных постов и т.п.
- gender ("male"|"female"|null): кого ищут.
- age_min, age_max (int|null): возрастной диапазон. Если возраст одной
  цифрой ("на роль 25 лет") — ставь age_min=age_max=25.
- project_types (list[str]): подмножество кодов:
  kino_serial, advertising, model_projects, show_reality, voice_dub, theater.
- role_types (list[str]): подмножество кодов:
  main, supporting, episode, massovka, groupovka, dubler, kaskader,
  model, photo_model, promo_model, tv_host, diktor, dancer, ballerina,
  gymnast, vocalist, musician.
- city (str|null): город съёмки на русском, если указан ("Москва", "Санкт-Петербург").
- rate (int|null): ставка в рублях за смену/съёмочный день. Если в тексте
  диапазон — бери нижнюю границу.
- summary (str|null): краткое описание до 30 слов.
- confidence (float, 0.0-1.0): твоя уверенность в извлечении.

Никаких комментариев, только JSON.
"""


def _try_parse_json(raw: str) -> dict[str, Any]:
    """Аккуратно достаём JSON из ответа модели (на случай, если она обернула ответ)."""
    raw = raw.strip()
    # Снять возможные markdown-обёртки
    if raw.startswith("```"):
        raw = raw.strip("`")
        # после strip('`') может остаться 'json\n{...}'
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    # Найти первую { и последнюю }
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"Не найден JSON в ответе LLM: {raw!r}")
    return json.loads(raw[start : end + 1])


class LLMProvider(ABC):
    """Базовый класс для LLM-провайдеров."""

    @abstractmethod
    async def _complete_json(self, system: str, user: str) -> str:
        """Возвращает «сырой» ответ модели (ожидается JSON-строка)."""

    async def extract(self, text: str) -> ExtractedData:
        """Извлечь структурированные данные из текста объявления."""
        try:
            raw = await self._complete_json(SYSTEM_PROMPT, text)
        except Exception as e:  # noqa: BLE001
            logger.exception("LLM call failed: {}", e)
            return ExtractedData(confidence=0.0)

        try:
            data = _try_parse_json(raw)
            parsed = ExtractedData(**data)
        except (ValueError, ValidationError, json.JSONDecodeError) as e:
            logger.warning("Не удалось распарсить ответ LLM: {} | raw={!r}", e, raw)
            return ExtractedData(confidence=0.0)

        normalized = normalize_extracted(parsed)
        if normalized.project_types != parsed.project_types:
            logger.debug(
                "Нормализация project_types: {} -> {}",
                parsed.project_types, normalized.project_types,
            )
        if normalized.role_types != parsed.role_types:
            logger.debug(
                "Нормализация role_types: {} -> {}",
                parsed.role_types, normalized.role_types,
            )
        return normalized
