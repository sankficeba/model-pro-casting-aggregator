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


def test_compose_greeting_and_link():
    out = compose_response(_rp(), "Главная роль", "https://t.me/channel/123")
    assert out.startswith("Здравствуйте, откликаюсь на Главная роль")
    assert "https://t.me/channel/123" in out


def test_compose_no_labels():
    out = compose_response(_rp(), "Актёр")
    assert "ФИО:" not in out
    assert "Возраст:" not in out
    assert "Телефон:" not in out
    assert "Иван Иванов" in out
    assert "28" in out
    assert "+79991234567" in out


def test_compose_creative_includes_sizes():
    out = compose_response(_rp("creative", height_cm=178, clothing_size=46), "Актёр")
    assert "178 / 46" in out


def test_compose_event_includes_sizes():
    out = compose_response(_rp("event", height_cm=170, clothing_size=44), "Хостес")
    assert "170 / 44" in out


def test_compose_general_no_sizes():
    out = compose_response(_rp("general", height_cm=180, clothing_size=48), "Хелпер")
    assert "180 / 48" not in out
    assert "Рост" not in out


def test_compose_admin_no_sizes():
    out = compose_response(_rp("admin"), "Оператор регистрации")
    assert "Рост" not in out


def test_compose_experience_text_no_label():
    out = compose_response(
        _rp("event", experience_text="Работал на ПМЭФ 2023"),
        "Промо-работник",
    )
    assert "Работал на ПМЭФ 2023" in out
    assert "Опыт:" not in out


def test_compose_creative_skills_no_label():
    out = compose_response(
        _rp("creative", skills_dance=["ballroom"], has_experience=None),
        "Танцор",
    )
    assert "Бальные" in out
    assert "Навыки:" not in out


def test_compose_creative_has_experience_fallback():
    out = compose_response(
        _rp("creative", skills_sport=[], skills_dance=[], skills_vocal=[],
            skills_instruments=[], has_experience=True, experience_text=None),
        "Актёр",
    )
    assert "Опыт съёмок есть" in out


def test_compose_no_link_when_none():
    out = compose_response(_rp(), "Роль", None)
    assert "t.me" not in out


def test_compose_no_phone_skipped():
    out = compose_response(_rp("general", phone=None), "Грузчик")
    assert "—" not in out


def test_compose_no_age_omitted():
    out = compose_response(_rp("admin", actual_age=None), "Супервайзер")
    lines = out.splitlines()
    assert not any(line.strip().isdigit() for line in lines)
