"""Юнит-тесты диспатчера: effective_cat = vacancy.category or post.category,
неизвестная категория → пропуск."""
from db.matching import _resolve_effective_category
from models.schemas import PostExtraction, VacancyExtraction


def test_resolve_uses_vacancy_category_when_set():
    post = PostExtraction(is_casting=True, category="event")
    v = VacancyExtraction(category="creative")
    assert _resolve_effective_category(post, v) == "creative"


def test_resolve_falls_back_to_post_category():
    post = PostExtraction(is_casting=True, category="event")
    v = VacancyExtraction(category=None)
    assert _resolve_effective_category(post, v) == "event"


def test_resolve_returns_none_when_both_none():
    post = PostExtraction(is_casting=True, category=None)
    v = VacancyExtraction(category=None)
    assert _resolve_effective_category(post, v) is None


def test_resolve_hybrid_post_helper_in_admin_post():
    """Гибридный пост: хелпер (general) в admin-посте.

    LLM должен выставить category="general" явно на вакансии хелпера,
    иначе он унаследует "admin" и до GeneralProfile-пользователей не дойдёт.
    """
    post = PostExtraction(is_casting=True, category="admin")
    helper_vacancy = VacancyExtraction(work_types=["helper"], category="general")
    admin_vacancy = VacancyExtraction(work_types=["registration_operator"], category=None)
    assert _resolve_effective_category(post, helper_vacancy) == "general"
    assert _resolve_effective_category(post, admin_vacancy) == "admin"
