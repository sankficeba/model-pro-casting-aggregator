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
