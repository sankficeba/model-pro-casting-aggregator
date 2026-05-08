"""Юнит-тесты per-vacancy match для event-категории."""
from db.matching import _check_event_match
from db.models import EventProfile
from models.schemas import PostExtraction, VacancyExtraction


def _profile(**kw) -> EventProfile:
    p = EventProfile(
        user_id=1,
        full_name="Test",
        gender="female",
        city="Москва",
        ready_for_travel=False,
        actual_age=22,
        min_rate=3000,
        height_cm=170,
        body_type=["slim"],
        hair_color="brown",
        hair_length="long",
        ethnicity=["slavic"],
        work_types=["hostess", "promo_model"],
    )
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def _post(**kw) -> PostExtraction:
    base = dict(is_casting=True, category="event", city="Москва", confidence=0.9)
    base.update(kw)
    return PostExtraction(**base)


def _vacancy(**kw) -> VacancyExtraction:
    base = dict(work_types=["hostess"], gender="female", age_min=18, age_max=30)
    base.update(kw)
    return VacancyExtraction(**base)


def test_event_match_basic():
    assert _check_event_match(_profile(), _post(), _vacancy()) is True


def test_event_match_work_types_no_overlap():
    assert _check_event_match(_profile(work_types=["promo_model"]), _post(), _vacancy(work_types=["animator"])) is False


def test_event_match_work_types_empty_in_vacancy_means_no_filter():
    """Если в вакансии work_types пуст — фильтр не применяем."""
    assert _check_event_match(_profile(), _post(), _vacancy(work_types=[])) is True


def test_event_match_age_uses_actual_age_not_play_age():
    p = _profile(actual_age=35)
    v = _vacancy(age_min=18, age_max=25)
    assert _check_event_match(p, _post(), v) is False


def test_event_match_city_mismatch_blocks_unless_travel():
    p = _profile(city="СПб", ready_for_travel=False)
    assert _check_event_match(p, _post(city="Москва"), _vacancy()) is False
    p.ready_for_travel = True
    assert _check_event_match(p, _post(city="Москва"), _vacancy()) is True


def test_event_match_rate_below_min_blocks():
    p = _profile(min_rate=5000)
    v = _vacancy()
    v.rate = 3000
    assert _check_event_match(p, _post(), v) is False


def test_event_match_gender_mismatch_blocks():
    p = _profile(gender="female")
    v = _vacancy(gender="male")
    assert _check_event_match(p, _post(), v) is False


def test_event_match_height_out_of_range_blocks():
    p = _profile(height_cm=160)
    v = _vacancy(height_min=170, height_max=180)
    assert _check_event_match(p, _post(), v) is False


def test_event_match_body_type_no_overlap_blocks():
    p = _profile(body_type=["plus_size"])
    v = _vacancy(body_type=["athletic"])
    assert _check_event_match(p, _post(), v) is False


def test_event_match_optional_filters_when_vacancy_empty():
    """Если у вакансии не указаны body_type/hair_color/ethnicity/height — не фильтруем."""
    p = _profile(body_type=[], hair_color=None, ethnicity=[])
    v = _vacancy()  # без физ. требований
    assert _check_event_match(p, _post(), v) is True
