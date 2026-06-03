"""Тесты bot.response.compose_response — сборка отклика по шаблону."""
from __future__ import annotations

from db.repository import ResponseProfile
from bot.response import compose_response


def _rp(category: str = "creative", **kw) -> ResponseProfile:
    base = dict(
        category=category,
        full_name="Иван Иванов",
        actual_age=28,
        phone="+79991234567",
        height_cm=180,
        clothing_size=48,
        shoe_size=42,
        experience_text=None,
        has_experience=True,
        skills_sport=[],
        skills_dance=[],
        skills_vocal=[],
        skills_instruments=[],
    )
    base.update(kw)
    return ResponseProfile(**base)


def test_compose_basic_creative():
    out = compose_response(_rp("creative"), "Главная роль")
    assert "Откликаюсь: Главная роль" in out
    assert "ФИО: Иван Иванов" in out
    assert "Возраст: 28" in out
    assert "Телефон: +79991234567" in out
    assert "180" in out
    assert "48" in out


def test_compose_event_includes_sizes():
    out = compose_response(_rp("event", height_cm=170, clothing_size=46), "Хостес")
    assert "Откликаюсь: Хостес" in out
    assert "170 / 46" in out


def test_compose_general_no_sizes():
    out = compose_response(_rp("general", height_cm=180, clothing_size=48), "Хелпер")
    assert "Откликаюсь: Хелпер" in out
    assert "Рост / размеры" not in out


def test_compose_admin_no_sizes():
    out = compose_response(_rp("admin"), "Оператор регистрации")
    assert "Рост / размеры" not in out


def test_compose_experience_text_shown():
    out = compose_response(
        _rp("event", experience_text="Работал на ПМЭФ 2023, форум Skolkovo"),
        "Промо-работник",
    )
    assert "Опыт: Работал на ПМЭФ 2023, форум Skolkovo" in out


def test_compose_creative_skills_shown():
    out = compose_response(
        _rp("creative", skills_dance=["ballroom", "hip_hop"], has_experience=None),
        "Танцор",
    )
    assert "Навыки:" in out
    assert "Бальные" in out


def test_compose_creative_has_experience_fallback():
    out = compose_response(
        _rp("creative", skills_sport=[], skills_dance=[], skills_vocal=[],
            skills_instruments=[], has_experience=True, experience_text=None),
        "Актёр",
    )
    assert "Опыт съёмок: есть" in out


def test_compose_no_phone_shows_dash():
    out = compose_response(_rp("general", phone=None), "Грузчик")
    assert "Телефон: —" in out


def test_compose_no_age_omitted():
    out = compose_response(_rp("admin", actual_age=None), "Супервайзер")
    assert "Возраст" not in out
