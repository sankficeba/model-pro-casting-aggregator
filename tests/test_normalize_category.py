"""Перенос вакансии в категорию её типов работ + новые типы работ."""
import pytest

from llm.normalize import normalize_extracted
from models.schemas import PostExtraction, VacancyExtraction as V


def _run(post_category, vacancies):
    post = PostExtraction(is_casting=True, category=post_category, confidence=0.9, vacancies=vacancies)
    return [(v.category, v.work_types) for v in normalize_extracted(post).vacancies]


@pytest.mark.parametrize("post_cat,work_types,expected_cat", [
    ("event", ["helper"], "general"),                 # хелпер на мероприятие → разнорабочие
    ("general", ["promo_model"], "event"),
    ("event", ["registration_operator"], "admin"),
    ("event", ["hostess"], None),                     # уже в своей категории — не трогаем
    ("event", ["hostess", "helper"], None),           # смешанные — не трогаем
    ("creative", ["helper"], None),                   # creative не переносим
])
def test_fix_category(post_cat, work_types, expected_cat):
    [(cat, wt)] = _run(post_cat, [V(work_types=work_types)])
    assert cat == expected_cat
    assert wt == work_types


@pytest.mark.parametrize("raw,expected", [
    (["promoter", "audience", "catering"], ["promoter", "audience", "catering"]),
    (["Промоутер / консультант", "Зрители на съёмках"], ["promoter", "audience"]),
    (["warehouse", "security"], ["warehouse", "security"]),
])
def test_new_work_types_are_known(raw, expected):
    [(_, wt)] = _run("event", [V(work_types=raw)])
    assert wt == expected


def test_profile_schemas_accept_new_work_types():
    from api.schemas import EventProfileSchema, GeneralProfileSchema

    EventProfileSchema(work_types=["promoter", "audience", "catering"])
    GeneralProfileSchema(work_types=["warehouse", "security"])
