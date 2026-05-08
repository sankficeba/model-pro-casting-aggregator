"""Абстрактный интерфейс LLM-провайдера."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger
from pydantic import ValidationError

from llm.normalize import normalize_extracted
from models.schemas import PostExtraction

SYSTEM_PROMPT = """Ты разбираешь объявления о работе и кастингах из
Telegram-каналов. Из присланного сообщения нужно извлечь параметры
поиска и вернуть СТРОГО JSON-объект без markdown-обёрток.

Категория поста (post.category) — доминирующее направление:
- "creative"  — кастинги в кино/сериалы/рекламу/театр/модельные проекты;
                роли: актёры, модели, фотомодели, дикторы, ведущие, танцоры.
- "event"     — мероприятия, презентации, корпоративы;
                роли: хостес, промо-модели, аниматоры.
- "general"   — разнорабочие на event/съёмки;
                роли: хелпер, клининг, грузчик.
- "admin"     — администрирование на мероприятиях;
                роли: оператор регистрации, супервайзер.

Структура поста:
{
  "is_casting": bool,                    // это объявление о работе?
                                         // false для рекламы услуг, обучения и т.п.
  "category": str|null,                  // доминирующая категория:
                                         // "creative"|"event"|"general"|"admin"
                                         // null если не входит в список
                                         // или is_casting=false
  "project_types": [str],                // только для creative; подмножество кодов:
                                         // kino_serial, advertising, model_projects,
                                         // show_reality, voice_dub, theater
                                         // Для event/general/admin — пустой массив.
  "city": str|null,                      // город на русском
  "summary": str|null,                   // краткое описание поста до 30 слов
  "confidence": float,                   // 0.0-1.0, твоя уверенность
  "vacancies": [                         // список ролей; пустой если is_casting=false
    {
      "role_types": [str],               // ТОЛЬКО для creative. Подмножество кодов:
                                         // main, supporting, episode, massovka,
                                         // groupovka, dubler, kaskader, model,
                                         // photo_model, promo_model, tv_host, diktor,
                                         // dancer, ballerina, gymnast, vocalist, musician.
                                         // Для event/general/admin — пустой массив.
      "work_types": [str],               // ТОЛЬКО для event/general/admin:
                                         // - event: hostess, promo_model, animator
                                         // - general: helper, cleaning, loader
                                         // - admin: registration_operator, supervisor
                                         // Для creative — пустой массив.
      "category": str|null,              // null = наследовать post.category;
                                         // указывать только если эта роль явно из
                                         // другой категории чем доминирующая
                                         // (редкие гибрид-посты).
      "gender": "male"|"female"|null,    // кого ищут на эту роль
      "age_min": int|null,               // нижний возраст; для одного значения 25 — age_min=age_max=25
      "age_max": int|null,
      "rate": int|null,                  // ставка в рублях за смену; диапазон — нижняя граница
      "ethnicity": [str],                 // подмножество кодов внешности (только creative/event):
                                          // slavic, european, caucasian, asian,
                                          // central_asian, african, arab, latin,
                                          // mixed, other.
                                          // Пустой массив если не указано или
                                          // не релевантно (general/admin).
      "height_min": int|null,             // рост в см, нижняя граница
      "height_max": int|null,             // рост в см, верхняя граница;
                                          // одно значение "рост 180" → height_min=height_max=180
      "body_type": [str],                 // подмножество кодов телосложения
                                          // (только creative/event):
                                          // slim, athletic, normal, plus_size, muscular.
      "hair_color": [str],                // подмножество цветов волос (creative/event):
                                          // black, dark_brown, brown, light_brown,
                                          // blond, red, grey, dyed.
      "hair_length": [str],               // подмножество кодов длины волос (creative/event):
                                          // bald, very_short, short, medium, long, very_long.
      "description": str|null,           // фрагмент поста об этой роли
      "role_label": str|null             // короткое имя роли как в посте: "Мама", "Сын", "Прохожий", "Хостес"
    }
  ]
}

ВАЖНО:
- Если в посте описана одна роль — vacancies массив длины 1.
- Если описаны несколько разных ролей с разными условиями (возрастом,
  гонораром, полом, внешностью, ростом, типом работы) — заводи на каждую отдельную
  запись в vacancies.
- Если is_casting=false — vacancies должно быть пустым массивом, category=null.
- Для creative-вакансий заполняй role_types, work_types оставь пустым.
- Для event/general/admin вакансий заполняй work_types, role_types оставь пустым.
- Никаких комментариев, только JSON.
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

    async def extract(self, text: str) -> PostExtraction:
        """Извлечь структурированные данные из текста объявления."""
        try:
            raw = await self._complete_json(SYSTEM_PROMPT, text)
        except Exception as e:  # noqa: BLE001
            logger.exception("LLM call failed: {}", e)
            return PostExtraction(confidence=0.0)

        try:
            data = _try_parse_json(raw)
            parsed = PostExtraction(**data)
        except (ValueError, ValidationError, json.JSONDecodeError) as e:
            logger.warning("Не удалось распарсить ответ LLM: {} | raw={!r}", e, raw)
            return PostExtraction(confidence=0.0)

        # Согласованность: is_casting=true без вакансий — бессмысленно.
        if parsed.is_casting and not parsed.vacancies:
            logger.warning(
                "LLM вернул is_casting=true с пустым vacancies — форсим is_casting=false"
            )
            parsed = parsed.model_copy(update={"is_casting": False})

        normalized = normalize_extracted(parsed)
        if normalized.project_types != parsed.project_types:
            logger.debug(
                "Нормализация project_types: {} -> {}",
                parsed.project_types, normalized.project_types,
            )
        return normalized
