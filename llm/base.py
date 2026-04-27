"""Абстрактный интерфейс LLM-провайдера."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger
from pydantic import ValidationError

from models.schemas import ExtractedData

SYSTEM_PROMPT = """Ты — профессиональный аналитик объявлений. Твоя задача:
извлечь из текста сообщения структурированную информацию.

Верни СТРОГО JSON-объект без какого-либо лишнего текста и без markdown-обёрток.

Ключи:
- gender: "male", "female" или null, если не указано.
- age: целое число или null, если не указано.
- category: краткая категория услуги/заявки на русском языке (например, "обучение",
  "работа", "услуга", "аренда", "покупка"), либо null.
- summary: краткое описание заявки до 20 слов, либо null.
- confidence: число от 0.0 до 1.0 — уверенность в извлечении.

Если данных для поля нет — ставь null. Никаких комментариев, только JSON.
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
            return ExtractedData(**data)
        except (ValueError, ValidationError, json.JSONDecodeError) as e:
            logger.warning("Не удалось распарсить ответ LLM: {} | raw={!r}", e, raw)
            return ExtractedData(confidence=0.0)
