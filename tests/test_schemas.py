"""Контракт PostExtraction / VacancyExtraction."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from models.schemas import PostExtraction, VacancyExtraction


def test_vacancy_minimal_defaults():
    v = VacancyExtraction()
    assert v.role_types == []
    assert v.gender is None
    assert v.age_min is None
    assert v.age_max is None
    assert v.rate is None
    assert v.description is None
    assert v.role_label is None


def test_post_minimal_defaults():
    p = PostExtraction()
    assert p.is_casting is False
    assert p.project_types == []
    assert p.city is None
    assert p.summary is None
    assert p.confidence == 0.0
    assert p.vacancies == []


def test_post_with_vacancies():
    p = PostExtraction(
        is_casting=True,
        project_types=["kino_serial"],
        city="Москва",
        summary="Сериал XYZ — 2 роли",
        confidence=0.9,
        vacancies=[
            VacancyExtraction(
                role_types=["main"], gender="female",
                age_min=35, age_max=45, rate=8000,
                description="Мама — 35–45, ставка 8000₽",
                role_label="Мама",
            ),
            VacancyExtraction(
                role_types=["episode"], gender="male",
                age_min=8, age_max=10, rate=5000,
                description="Сын — 8–10 лет",
                role_label="Сын",
            ),
        ],
    )
    assert len(p.vacancies) == 2
    assert p.vacancies[0].role_label == "Мама"
    assert p.vacancies[1].age_min == 8


def test_age_validation_bounds():
    with pytest.raises(ValidationError):
        VacancyExtraction(age_min=-1)
    with pytest.raises(ValidationError):
        VacancyExtraction(age_max=200)


def test_confidence_bounds():
    with pytest.raises(ValidationError):
        PostExtraction(confidence=1.5)
    with pytest.raises(ValidationError):
        PostExtraction(confidence=-0.1)


def test_extracted_data_no_longer_exists():
    """Убедимся, что старая модель удалена — никто не должен на неё ссылаться."""
    import models.schemas as m
    assert not hasattr(m, "ExtractedData")
