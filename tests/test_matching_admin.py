"""Юнит-тесты per-vacancy match для admin-категории."""
from db.matching import _check_admin_match
from db.models import AdminProfile
from models.schemas import PostExtraction, VacancyExtraction


def _profile(**kw) -> AdminProfile:
    p = AdminProfile(
        user_id=1,
        full_name="Test",
        gender="female",
        city="Москва",
        ready_for_travel=False,
        actual_age=28,
        min_rate=2500,
        work_types=["registration_operator"],
    )
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def _post(**kw) -> PostExtraction:
    base = dict(is_casting=True, category="admin", city="Москва", confidence=0.9)
    base.update(kw)
    return PostExtraction(**base)


def _vacancy(**kw) -> VacancyExtraction:
    base = dict(work_types=["registration_operator"], age_min=20, age_max=40)
    base.update(kw)
    return VacancyExtraction(**base)


def test_admin_match_basic():
    assert _check_admin_match(_profile(), _post(), _vacancy()) is True


def test_admin_match_work_types_no_overlap():
    assert _check_admin_match(_profile(), _post(), _vacancy(work_types=["supervisor"])) is False


def test_admin_match_age_uses_actual_age():
    assert _check_admin_match(_profile(actual_age=50), _post(), _vacancy(age_min=20, age_max=40)) is False


def test_admin_match_does_not_filter_on_gender():
    """admin: gender не используется как гейт (часто не указывается в вакансии)."""
    p = _profile(gender="male")
    v = _vacancy(gender="female")
    assert _check_admin_match(p, _post(), v) is True


def test_admin_match_city_mismatch_blocks_unless_travel():
    p = _profile(city="СПб")
    assert _check_admin_match(p, _post(city="Москва"), _vacancy()) is False
    p.ready_for_travel = True
    assert _check_admin_match(p, _post(city="Москва"), _vacancy()) is True


def test_admin_match_rate_below_min_blocks():
    p = _profile(min_rate=5000)
    v = _vacancy()
    v.rate = 2000
    assert _check_admin_match(p, _post(), v) is False
