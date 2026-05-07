"""Конвертер ORM Message + Vacancy → Pydantic PostExtraction + VacancyExtraction.

Используется в duplicate-пути _handle_message: грузим canonical из
БД и конвертируем для прогона через find_matching_vacancies."""
from datetime import datetime, timezone

from db.matching import _orm_to_extractions
from db.models import Message, Vacancy


def _make_message(**overrides) -> Message:
    msg = Message(
        id=1,
        tg_chat_id=-1001234,
        tg_chat_username="ch",
        tg_message_id=42,
        text="Test",
        text_hash="a" * 40,
        is_casting=True,
        gender="female",
        age_min=18,
        age_max=25,
        project_types=["advertising"],
        role_types=["main"],
        city="Москва",
        rate=10000,
        summary="summary",
        confidence=0.95,
        received_at=datetime.now(timezone.utc),
    )
    for k, v in overrides.items():
        setattr(msg, k, v)
    return msg


def _make_vacancy(**overrides) -> Vacancy:
    vac = Vacancy(
        id=1,
        message_id=1,
        idx=0,
        role_types=["main"],
        gender="female",
        age_min=20,
        age_max=30,
        rate=15000,
        ethnicity=["slavic"],
        height_min=160,
        height_max=180,
        body_type=["athletic"],
        hair_color=["brown"],
        hair_length=["medium"],
        description="desc",
        role_label="Главная роль",
    )
    for k, v in overrides.items():
        setattr(vac, k, v)
    return vac


def test_orm_to_extractions_post_fields():
    msg = _make_message()
    post, vacs = _orm_to_extractions(msg, [])
    assert post.is_casting is True
    assert post.project_types == ["advertising"]
    assert post.city == "Москва"
    assert post.summary == "summary"
    assert post.confidence == 0.95
    assert vacs == []


def test_orm_to_extractions_vacancy_fields():
    msg = _make_message()
    vac = _make_vacancy()
    _, vacs = _orm_to_extractions(msg, [vac])
    assert len(vacs) == 1
    v = vacs[0]
    assert v.role_types == ["main"]
    assert v.gender == "female"
    assert v.age_min == 20
    assert v.age_max == 30
    assert v.rate == 15000
    assert v.ethnicity == ["slavic"]
    assert v.height_min == 160
    assert v.height_max == 180
    assert v.body_type == ["athletic"]
    assert v.hair_color == ["brown"]
    assert v.hair_length == ["medium"]
    assert v.description == "desc"
    assert v.role_label == "Главная роль"


def test_orm_to_extractions_multiple_vacancies_preserves_order():
    msg = _make_message()
    v1 = _make_vacancy(id=1, idx=0, role_label="Первая")
    v2 = _make_vacancy(id=2, idx=1, role_label="Вторая")
    _, vacs = _orm_to_extractions(msg, [v1, v2])
    assert [v.role_label for v in vacs] == ["Первая", "Вторая"]


def test_orm_to_extractions_handles_nullable_fields():
    msg = _make_message(gender=None, age_min=None, age_max=None, rate=None, summary=None, city=None)
    vac = _make_vacancy(gender=None, age_min=None, age_max=None, rate=None, role_label=None, description=None)
    post, vacs = _orm_to_extractions(msg, [vac])
    assert post.city is None
    assert post.summary is None
    assert vacs[0].gender is None
    assert vacs[0].role_label is None
