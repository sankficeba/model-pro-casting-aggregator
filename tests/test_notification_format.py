"""Юнит-тест на _format_notification: одна агрегированная карточка
со списком подошедших ролей."""
from __future__ import annotations

from dataclasses import dataclass

from models.schemas import PostExtraction, VacancyExtraction
from userbot.client import Userbot


@dataclass
class FakeMsg:
    id: int = 42
    message: str = "raw text"


def _post() -> PostExtraction:
    return PostExtraction(
        is_casting=True,
        project_types=["kino_serial"],
        city="Москва",
        summary="Сериал «X» — кастинг",
        confidence=0.9,
    )


def test_format_two_matched_vacancies():
    post = _post()
    vacancies = [
        VacancyExtraction(role_types=["main"], gender="female",
                          age_min=35, age_max=45, rate=8000,
                          description="Мама", role_label="Мама"),
        VacancyExtraction(role_types=["episode"], gender="male",
                          age_min=8, age_max=10, rate=5000,
                          description="Сын", role_label="Сын"),
    ]
    txt = Userbot._format_notification(
        post=post, vacancies=vacancies, matched_idxs=[0, 1],
        message=FakeMsg(), chat_username="castings_ch",
    )
    assert "Подходящий кастинг" in txt
    assert "Мама" in txt
    assert "Сын" in txt
    assert "8000" in txt
    assert "5000" in txt
    assert "Москва" in txt
    assert "https://t.me/castings_ch/42" in txt


def test_format_one_matched_vacancy_role_label_fallback():
    """Без role_label — карточка не должна показывать тех. код."""
    post = _post()
    vacancies = [
        VacancyExtraction(role_types=["main"], gender="female",
                          age_min=20, age_max=25, rate=5000,
                          description="Главная героиня"),
    ]
    txt = Userbot._format_notification(
        post=post, vacancies=vacancies, matched_idxs=[0],
        message=FakeMsg(), chat_username=None,
    )
    # Не должно быть голого "main" в карточке
    assert "main" not in txt.split("Открыть")[0]
    # Должен быть либо description, либо русский label роли
    assert "героин" in txt.lower() or "Главная" in txt
