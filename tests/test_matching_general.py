"""Юнит-тесты per-vacancy match для general-категории."""
from db.matching import _check_general_match
from db.models import GeneralProfile
from models.schemas import PostExtraction, VacancyExtraction


def _profile(**kw) -> GeneralProfile:
    p = GeneralProfile(
        user_id=1,
        full_name="Test",
        gender="male",
        city="Москва",
        ready_for_travel=False,
        actual_age=30,
        min_rate=2000,
        work_types=["loader", "helper"],
    )
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def _post(**kw) -> PostExtraction:
    base = dict(is_casting=True, category="general", city="Москва", confidence=0.9)
    base.update(kw)
    return PostExtraction(**base)


def _vacancy(**kw) -> VacancyExtraction:
    base = dict(work_types=["loader"], age_min=18, age_max=50)
    base.update(kw)
    return VacancyExtraction(**base)


def test_general_match_basic():
    assert _check_general_match(_profile(), _post(), _vacancy()) is True


def test_general_match_work_types_no_overlap():
    assert _check_general_match(_profile(work_types=["cleaning"]), _post(), _vacancy(work_types=["loader"])) is False


def test_general_match_work_types_empty_in_vacancy():
    assert _check_general_match(_profile(), _post(), _vacancy(work_types=[])) is True


def test_general_match_age_uses_actual_age():
    assert _check_general_match(_profile(actual_age=60), _post(), _vacancy(age_min=18, age_max=50)) is False


def test_general_match_gender_mismatch_blocks():
    assert _check_general_match(_profile(gender="female"), _post(), _vacancy(gender="male")) is False


def test_general_match_rate_below_min_blocks():
    p = _profile(min_rate=5000)
    v = _vacancy()
    v.rate = 1500
    assert _check_general_match(p, _post(), v) is False


def test_general_match_does_not_filter_on_creative_fields():
    """ethnicity / body_type / hair / role_types / project_types — не используются."""
    v = _vacancy(ethnicity=["asian"], body_type=["athletic"], hair_color=["blond"])
    assert _check_general_match(_profile(), _post(), v) is True
