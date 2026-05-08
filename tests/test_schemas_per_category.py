"""Pydantic-валидация per-category схем."""
import pytest
from pydantic import ValidationError

from api.schemas import (
    AdminProfileSchema,
    CreativeProfileSchema,
    EventProfileSchema,
    GeneralProfileSchema,
)
from models.schemas import PostExtraction, VacancyExtraction


def test_creative_profile_accepts_full_data():
    s = CreativeProfileSchema(
        full_name="Иван Петров",
        gender="male",
        city="Москва",
        actual_age=25,
        play_age_min=20,
        play_age_max=30,
        project_types=["advertising", "movie"],
        role_types=["main"],
        min_rate=5000,
        height_cm=180,
        ethnicity=["slavic"],
        body_type=["athletic"],
        hair_color="brown",
        hair_length="short",
        has_experience=True,
        education="higher",
        tax_status="self_employed",
        phone="+79991234567",
        telegram_user="ivan_p",
        email="ivan@example.com",
    )
    assert s.full_name == "Иван Петров"


def test_event_profile_work_types_validates():
    EventProfileSchema(work_types=["hostess", "animator"])
    with pytest.raises(ValidationError):
        EventProfileSchema(work_types=["invalid_value"])


def test_general_profile_physical_fitness_enum():
    GeneralProfileSchema(physical_fitness="medium")
    with pytest.raises(ValidationError):
        GeneralProfileSchema(physical_fitness="extra_heavy")


def test_general_profile_work_types_validates():
    GeneralProfileSchema(work_types=["helper", "loader"])
    with pytest.raises(ValidationError):
        GeneralProfileSchema(work_types=["actor"])


def test_admin_profile_work_types_validates():
    AdminProfileSchema(work_types=["registration_operator", "supervisor"])
    with pytest.raises(ValidationError):
        AdminProfileSchema(work_types=["hostess"])


def test_email_format_required():
    with pytest.raises(ValidationError):
        CreativeProfileSchema(email="not-an-email")


def test_all_optional_fields_can_be_omitted():
    """Draft-сохранение: PUT приходит с любым подмножеством полей."""
    CreativeProfileSchema()
    EventProfileSchema()
    GeneralProfileSchema()
    AdminProfileSchema()


def test_post_extraction_accepts_category():
    p = PostExtraction(is_casting=True, category="event", confidence=0.8)
    assert p.category == "event"


def test_post_extraction_rejects_invalid_category():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PostExtraction(is_casting=True, category="invalid")


def test_post_extraction_category_optional():
    p = PostExtraction(is_casting=False)
    assert p.category is None


def test_vacancy_extraction_accepts_work_types_and_category():
    v = VacancyExtraction(
        work_types=["hostess", "animator"],
        category="event",
        gender="female",
    )
    assert v.work_types == ["hostess", "animator"]
    assert v.category == "event"


def test_vacancy_extraction_defaults_empty_work_types():
    v = VacancyExtraction()
    assert v.work_types == []
    assert v.category is None
