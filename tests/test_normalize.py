"""normalize_extracted: канонизация project_types/role_types на обоих уровнях."""
from __future__ import annotations

from models.schemas import PostExtraction, VacancyExtraction
from llm.normalize import normalize_extracted


def test_normalizes_post_project_types():
    p = PostExtraction(
        is_casting=True,
        project_types=["реклама", "kino_serial"],  # label + code
    )
    out = normalize_extracted(p)
    assert "advertising" in out.project_types
    assert "kino_serial" in out.project_types


def test_normalizes_per_vacancy_role_types():
    p = PostExtraction(
        is_casting=True,
        vacancies=[
            VacancyExtraction(role_types=["Главная"]),  # label
            VacancyExtraction(role_types=["episode", "trash-неизвестный"]),
        ],
    )
    out = normalize_extracted(p)
    assert out.vacancies[0].role_types == ["main"]
    assert out.vacancies[1].role_types == ["episode"]  # неизвестный код выкинули


def test_normalizes_per_vacancy_ethnicity():
    p = PostExtraction(
        is_casting=True,
        vacancies=[
            VacancyExtraction(ethnicity=["Азиатский", "slavic"]),  # label + code
            VacancyExtraction(ethnicity=["мусор", "arab"]),
        ],
    )
    out = normalize_extracted(p)
    assert out.vacancies[0].ethnicity == ["asian", "slavic"]
    assert out.vacancies[1].ethnicity == ["arab"]


def test_preserves_non_normalized_fields():
    p = PostExtraction(
        is_casting=True,
        city="Москва",
        confidence=0.7,
        vacancies=[
            VacancyExtraction(
                gender="female", age_min=20, age_max=30, rate=5000,
                description="d", role_label="Маша",
            ),
        ],
    )
    out = normalize_extracted(p)
    assert out.city == "Москва"
    assert out.confidence == 0.7
    v = out.vacancies[0]
    assert v.gender == "female"
    assert v.age_min == 20
    assert v.rate == 5000
    assert v.role_label == "Маша"


def test_normalize_event_work_types():
    p = PostExtraction(
        is_casting=True,
        category="event",
        vacancies=[
            VacancyExtraction(work_types=["hostess", "animator"]),
        ],
    )
    out = normalize_extracted(p)
    assert out.vacancies[0].work_types == ["hostess", "animator"]


def test_normalize_general_work_types():
    p = PostExtraction(
        is_casting=True,
        category="general",
        vacancies=[
            VacancyExtraction(work_types=["loader", "cleaning"]),
        ],
    )
    out = normalize_extracted(p)
    assert sorted(out.vacancies[0].work_types) == ["cleaning", "loader"]


def test_normalize_admin_work_types():
    p = PostExtraction(
        is_casting=True,
        category="admin",
        vacancies=[
            VacancyExtraction(work_types=["supervisor", "registration_operator"]),
        ],
    )
    out = normalize_extracted(p)
    assert sorted(out.vacancies[0].work_types) == ["registration_operator", "supervisor"]


def test_normalize_drops_unknown_work_types():
    p = PostExtraction(
        is_casting=True,
        category="event",
        vacancies=[
            VacancyExtraction(work_types=["hostess", "garbage_code"]),
        ],
    )
    out = normalize_extracted(p)
    assert out.vacancies[0].work_types == ["hostess"]


def test_normalize_passes_post_category():
    p = PostExtraction(is_casting=True, category="event", confidence=0.9)
    out = normalize_extracted(p)
    assert out.category == "event"
