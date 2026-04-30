"""Тесты bot.response.compose_response — сборка отклика по шаблону."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from api.schemas import ProfileResponse
from bot.response import compose_response


@dataclass
class FakeMessage:
    project_types: list[str]


@dataclass
class FakeVacancy:
    role_label: str | None = None
    role_types: list[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.role_types is None:
            self.role_types = []


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
