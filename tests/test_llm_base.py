"""LLMProvider.extract: парсинг JSON под PostExtraction + нормализация."""
from __future__ import annotations

import json

from llm.base import LLMProvider
from models.schemas import PostExtraction


class _FakeProvider(LLMProvider):
    def __init__(self, raw: str) -> None:
        self._raw = raw

    async def _complete_json(self, system: str, user: str) -> str:  # noqa: ARG002
        return self._raw


async def test_extract_multi_vacancy():
    raw = json.dumps({
        "is_casting": True,
        "project_types": ["реклама"],
        "city": "Москва",
        "summary": "Реклама бренда X",
        "confidence": 0.85,
        "vacancies": [
            {"role_types": ["main"], "gender": "female",
             "age_min": 25, "age_max": 35, "rate": 12000,
             "description": "Героиня — девушка 25–35", "role_label": "Героиня"},
            {"role_types": ["episode"], "gender": "male",
             "age_min": 30, "age_max": 40, "rate": 8000,
             "description": "Партнёр — мужчина 30–40", "role_label": "Партнёр"},
        ],
    })
    out = await _FakeProvider(raw).extract("ignored")
    assert isinstance(out, PostExtraction)
    assert out.is_casting is True
    assert out.project_types == ["advertising"]  # нормализовано
    assert len(out.vacancies) == 2
    assert out.vacancies[0].role_label == "Героиня"


async def test_extract_no_vacancies_forces_not_casting():
    """Если LLM сказал is_casting=true, но vacancies пусто — форсим false."""
    raw = json.dumps({"is_casting": True, "confidence": 0.9, "vacancies": []})
    out = await _FakeProvider(raw).extract("ignored")
    assert out.is_casting is False


async def test_extract_invalid_json_returns_zero_confidence():
    out = await _FakeProvider("not a json").extract("ignored")
    assert out.confidence == 0.0
    assert out.is_casting is False
    assert out.vacancies == []


async def test_extract_strips_markdown_wrapper():
    raw = "```json\n" + json.dumps({"is_casting": False, "vacancies": []}) + "\n```"
    out = await _FakeProvider(raw).extract("ignored")
    assert out.is_casting is False
