"""Тесты bot.response.compose_response — сборка отклика по шаблону."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

from api.schemas import ProfileResponse
from bot.response import compose_response, compose_response_llm
from llm.base import LLMProvider


@dataclass
class FakeMessage:
    project_types: list[str]
    city: str | None = None
    summary: str | None = None


@dataclass
class FakeVacancy:
    id: int = 1
    role_label: str | None = None
    role_types: list[str] = field(default_factory=list)
    gender: str | None = None
    age_min: int | None = None
    age_max: int | None = None
    rate: int | None = None
    ethnicity: list[str] = field(default_factory=list)
    height_min: int | None = None
    height_max: int | None = None
    body_type: list[str] = field(default_factory=list)
    hair_color: list[str] = field(default_factory=list)
    hair_length: list[str] = field(default_factory=list)
    description: str | None = None


def _profile(**kw) -> ProfileResponse:
    base = dict(
        user_id=1,
        full_name="Иван Иванов",
        gender="male",
        city="Москва",
        ready_for_travel=False,
        actual_age=28,
        play_age_min=25,
        play_age_max=32,
        project_types=["kino_serial"],
        role_types=["main"],
        min_rate=None,
        show_negotiable=False,
        show_noncommercial=True,
        show_agency=True,
        height_cm=180,
        clothing_size=None,
        shoe_size=None,
        ethnicity=["slavic"],
        body_type=["athletic"],
        hair_color="brown",
        hair_length="short",
        has_experience=True,
        education=None,
        tax_status=None,
        eye_color=None,
        marks=[],
        skills_sport=[],
        skills_dance=[],
        skills_vocal=[],
        skills_instruments=[],
        portfolio_url=None,
        video_url=None,
        professional_url=None,
        phone=None,
        vk_url=None,
        email=None,
        completion_pct=100,
    )
    base.update(kw)
    return ProfileResponse(**base)


def test_compose_basic():
    msg = FakeMessage(project_types=["kino_serial"])
    vac = FakeVacancy(role_label="Иван", role_types=["main"])
    out = compose_response(_profile(), msg, vac)  # type: ignore[arg-type]
    assert "Откликаюсь на роль «Иван»" in out
    assert "Кино и сериалы" in out  # project label
    assert "Иван Иванов" in out
    assert "28 лет" in out
    assert "25–32" in out
    assert "Москва" in out
    assert "180 см" in out
    assert "Опыт съёмок есть" in out


def test_compose_with_contacts():
    msg = FakeMessage(project_types=[])
    vac = FakeVacancy(role_types=["model"])
    p = _profile(
        phone="+79991234567",
        email="ivan@example.com",
        portfolio_url="https://example.com/portfolio",
    )
    out = compose_response(p, msg, vac)  # type: ignore[arg-type]
    assert "+79991234567" in out
    assert "ivan@example.com" in out
    assert "portfolio" in out


def test_compose_role_fallback_to_label_from_codes():
    """Если role_label не задан — берём русский label из справочника."""
    msg = FakeMessage(project_types=[])
    vac = FakeVacancy(role_label=None, role_types=["main"])
    out = compose_response(_profile(), msg, vac)  # type: ignore[arg-type]
    assert "«Главная»" in out


def test_compose_no_age_no_extras():
    """Анкета с минимумом данных — отклик не падает, поля скрываются."""
    msg = FakeMessage(project_types=[])
    vac = FakeVacancy(role_types=["episode"])
    p = _profile(
        actual_age=None,
        play_age_min=None,
        play_age_max=None,
        height_cm=None,
        body_type=[],
        ethnicity=[],
        hair_color=None,
        has_experience=None,
    )
    out = compose_response(p, msg, vac)  # type: ignore[arg-type]
    assert "Откликаюсь" in out
    assert "Параметры:" not in out
    assert "Опыт" not in out


# ---------- LLM-режим ----------


class _FakeLLM(LLMProvider):
    """Возвращает фиксированный JSON. Не делает сетевых вызовов."""

    def __init__(self, raw: str) -> None:
        self._raw = raw
        self.last_user: str | None = None

    async def _complete_json(self, system: str, user: str) -> str:  # noqa: ARG002
        self.last_user = user
        return self._raw


async def test_compose_llm_uses_llm_text():
    msg = FakeMessage(project_types=["kino_serial"], city="Москва")
    vac = FakeVacancy(role_label="Мама", role_types=["main"], age_min=35, age_max=45)
    raw = json.dumps({"text": "Здравствуйте! Очень хочу попробоваться на эту роль."})
    llm = _FakeLLM(raw)
    out = await compose_response_llm(_profile(), msg, vac, llm)  # type: ignore[arg-type]
    assert "Очень хочу попробоваться" in out


async def test_compose_llm_falls_back_on_invalid_json():
    """LLM вернул мусор — откатываемся на шаблон, не падаем."""
    msg = FakeMessage(project_types=[])
    vac = FakeVacancy(role_label="Лена", role_types=["main"])
    llm = _FakeLLM("not a json at all")
    out = await compose_response_llm(_profile(), msg, vac, llm)  # type: ignore[arg-type]
    assert "Откликаюсь на роль «Лена»" in out  # ⇐ из шаблона


async def test_compose_llm_payload_includes_vacancy_and_profile():
    """В user-payload передаются ключи candidate и vacancy."""
    msg = FakeMessage(project_types=[], city="Москва")
    vac = FakeVacancy(role_label="X", role_types=["main"])
    llm = _FakeLLM(json.dumps({"text": "ok"}))
    await compose_response_llm(_profile(), msg, vac, llm)  # type: ignore[arg-type]
    payload = json.loads(llm.last_user or "{}")
    assert "candidate" in payload and "vacancy" in payload
    assert payload["vacancy"]["role_label"] == "X"
    assert payload["candidate"]["full_name"] == "Иван Иванов"
