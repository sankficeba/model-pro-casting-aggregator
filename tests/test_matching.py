"""Юнит-тесты per-vacancy matching. Используем простые объекты,
имитирующие ActorProfile (без БД)."""
from __future__ import annotations

from dataclasses import dataclass, field

from db.matching import matches
from models.schemas import PostExtraction, VacancyExtraction


@dataclass
class FakeProfile:
    gender: str | None = None
    play_age_min: int | None = None
    play_age_max: int | None = None
    project_types: list[str] = field(default_factory=list)
    role_types: list[str] = field(default_factory=list)
    min_rate: int | None = None
    city: str | None = None
    ready_for_travel: bool = False
    ethnicity: list[str] = field(default_factory=list)
    height_cm: int | None = None
    body_type: list[str] = field(default_factory=list)
    hair_color: str | None = None
    hair_length: str | None = None


def _post(**kw) -> PostExtraction:
    return PostExtraction(is_casting=True, confidence=0.9, **kw)


def _v(**kw) -> VacancyExtraction:
    return VacancyExtraction(**kw)


def test_match_basic_age_overlap():
    p = _post()
    v = _v(age_min=20, age_max=30)
    prof = FakeProfile(play_age_min=25, play_age_max=35)
    assert matches(prof, p, v) is True


def test_no_match_age_disjoint():
    p = _post()
    v = _v(age_min=8, age_max=10)
    prof = FakeProfile(play_age_min=25, play_age_max=35)
    assert matches(prof, p, v) is False


def test_match_one_of_many_vacancies():
    """Анкета 35-летней женщины, в посте 2 вакансии: подходит только одна."""
    p = _post(project_types=["kino_serial"], city="Москва")
    v_mama = _v(role_types=["main"], gender="female",
                age_min=35, age_max=45, rate=8000)
    v_son  = _v(role_types=["episode"], gender="male",
                age_min=8, age_max=10, rate=5000)
    prof = FakeProfile(
        gender="female", play_age_min=33, play_age_max=40,
        project_types=["kino_serial"], role_types=["main"],
        min_rate=5000, city="Москва",
    )
    assert matches(prof, p, v_mama) is True
    assert matches(prof, p, v_son) is False


def test_post_level_city_filter():
    p = _post(city="Москва")
    v = _v(age_min=20, age_max=30)
    prof = FakeProfile(play_age_min=25, play_age_max=35, city="Казань")
    assert matches(prof, p, v) is False


def test_post_level_city_filter_ready_for_travel():
    p = _post(city="Москва")
    v = _v(age_min=20, age_max=30)
    prof = FakeProfile(
        play_age_min=25, play_age_max=35, city="Казань", ready_for_travel=True,
    )
    assert matches(prof, p, v) is True


def test_rate_below_user_minimum():
    p = _post()
    v = _v(rate=3000)
    prof = FakeProfile(min_rate=10000)
    assert matches(prof, p, v) is False


def test_project_types_intersection_post_level():
    p = _post(project_types=["advertising"])
    v = _v()
    prof = FakeProfile(project_types=["kino_serial"])
    assert matches(prof, p, v) is False


def test_role_types_intersection_vacancy_level():
    p = _post()
    v = _v(role_types=["dancer"])
    prof = FakeProfile(role_types=["main"])
    assert matches(prof, p, v) is False


def test_unspecified_fields_pass_through():
    """Поле не указано в посте/вакансии → фильтр по нему не применяется."""
    p = _post()
    v = _v()  # пусто
    prof = FakeProfile()
    assert matches(prof, p, v) is True


def test_ethnicity_mismatch_rejected():
    p = _post()
    v = _v(ethnicity=["asian"])
    prof = FakeProfile(ethnicity=["slavic"])
    assert matches(prof, p, v) is False


def test_ethnicity_intersection_accepted():
    p = _post()
    v = _v(ethnicity=["asian", "central_asian"])
    prof = FakeProfile(ethnicity=["central_asian", "mixed"])
    assert matches(prof, p, v) is True


def test_ethnicity_unspecified_in_profile_passes():
    """В вакансии ethnicity указан, у профиля — нет: фильтр не применяем."""
    p = _post()
    v = _v(ethnicity=["asian"])
    prof = FakeProfile(ethnicity=[])
    assert matches(prof, p, v) is True


def test_height_outside_range_rejected():
    p = _post()
    v = _v(height_min=170, height_max=180)
    prof = FakeProfile(height_cm=165)
    assert matches(prof, p, v) is False


def test_height_inside_range_accepted():
    p = _post()
    v = _v(height_min=170, height_max=180)
    prof = FakeProfile(height_cm=175)
    assert matches(prof, p, v) is True


def test_height_one_sided_min():
    """В вакансии задан только нижний предел, верхний — без ограничений."""
    p = _post()
    v = _v(height_min=180)
    prof = FakeProfile(height_cm=190)
    assert matches(prof, p, v) is True
    prof_low = FakeProfile(height_cm=170)
    assert matches(prof_low, p, v) is False


def test_height_unspecified_in_profile_passes():
    """В вакансии есть рост, в профиле height_cm=None: фильтр не применяем."""
    p = _post()
    v = _v(height_min=180, height_max=200)
    prof = FakeProfile(height_cm=None)
    assert matches(prof, p, v) is True


def test_body_type_intersection():
    p = _post()
    v = _v(body_type=["athletic", "muscular"])
    prof_match = FakeProfile(body_type=["athletic"])
    prof_miss = FakeProfile(body_type=["plus_size"])
    assert matches(prof_match, p, v) is True
    assert matches(prof_miss, p, v) is False


def test_hair_color_membership():
    """В вакансии перечислены допустимые цвета — у профиля один из них."""
    p = _post()
    v = _v(hair_color=["blond", "light_brown"])
    prof_blond = FakeProfile(hair_color="blond")
    prof_black = FakeProfile(hair_color="black")
    assert matches(prof_blond, p, v) is True
    assert matches(prof_black, p, v) is False


def test_hair_length_membership():
    p = _post()
    v = _v(hair_length=["long", "very_long"])
    prof_long = FakeProfile(hair_length="long")
    prof_short = FakeProfile(hair_length="short")
    assert matches(prof_long, p, v) is True
    assert matches(prof_short, p, v) is False


def test_hair_unspecified_in_profile_passes():
    p = _post()
    v = _v(hair_color=["blond"], hair_length=["long"])
    prof = FakeProfile(hair_color=None, hair_length=None)
    assert matches(prof, p, v) is True
