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
        category="creative",
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
    assert "Подходящая вакансия" in txt
    assert "Творческие позиции" in txt
    assert "Мама" in txt
    assert "Сын" in txt
    assert "8000" in txt
    assert "5000" in txt
    assert "Москва" in txt
    assert "https://t.me/castings_ch/42" in txt


def test_format_event_category_shows_work_types():
    """Для event-постов в шапке показывается «Event-персонал», а в meta —
    work_types из подошедших вакансий вместо project_types."""
    post = PostExtraction(
        is_casting=True,
        category="event",
        city="Москва",
        confidence=0.9,
    )
    vacancies = [
        VacancyExtraction(
            work_types=["hostess", "promo_model"],
            gender="female",
            age_min=18, age_max=30, rate=4000,
            role_label="Хостес",
        ),
    ]
    txt = Userbot._format_notification(
        post=post, vacancies=vacancies, matched_idxs=[0],
        message=FakeMsg(), chat_username=None,
        effective_category="event",
    )
    assert "Event-персонал" in txt
    assert "🎉" in txt
    assert "Должности:" in txt
    assert "Тип проекта:" not in txt
    # work_types должны рендериться как русские лейблы
    assert "Хостес" in txt or "Промо-модель" in txt


def test_format_general_category_emoji_and_label():
    post = PostExtraction(is_casting=True, category="general", city="СПб", confidence=0.9)
    vacancies = [
        VacancyExtraction(work_types=["loader"], age_min=18, age_max=50, rate=3000, role_label="Грузчик"),
    ]
    txt = Userbot._format_notification(
        post=post, vacancies=vacancies, matched_idxs=[0],
        message=FakeMsg(), chat_username=None,
        effective_category="general",
    )
    assert "Разнорабочие" in txt
    assert "🛠" in txt


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


def test_format_includes_height_and_ethnicity():
    post = _post()
    vacancies = [
        VacancyExtraction(role_types=["model"], gender="female",
                          age_min=20, age_max=30, rate=10000,
                          height_min=170, height_max=180,
                          ethnicity=["asian"],
                          role_label="Модель"),
    ]
    txt = Userbot._format_notification(
        post=post, vacancies=vacancies, matched_idxs=[0],
        message=FakeMsg(), chat_username=None,
    )
    assert "170" in txt and "180" in txt
    assert "asian" in txt or "рост" in txt.lower()
