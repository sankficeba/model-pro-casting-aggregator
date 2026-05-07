"""Чистая логика сбора autocomplete-suggestions из per-category профилей."""
from datetime import datetime, timezone

from db.repository import _collect_suggestions


def test_collect_suggestions_dedupes_values():
    """Если одно и то же значение лежит в двух профилях — отдаём один раз."""
    profiles = {
        "creative": {"city": "Москва", "phone": "+79991111111", "updated_at": datetime(2026, 5, 1, tzinfo=timezone.utc)},
        "event": {"city": "Москва", "phone": "+79992222222", "updated_at": datetime(2026, 5, 2, tzinfo=timezone.utc)},
    }
    result = _collect_suggestions(profiles)
    assert result["city"] == ["Москва"]
    assert sorted(result["phone"]) == ["+79991111111", "+79992222222"]


def test_collect_suggestions_orders_by_updated_at_desc():
    """Свежие значения первыми."""
    profiles = {
        "creative": {"city": "Москва", "updated_at": datetime(2026, 5, 1, tzinfo=timezone.utc)},
        "event": {"city": "СПб", "updated_at": datetime(2026, 5, 5, tzinfo=timezone.utc)},
    }
    result = _collect_suggestions(profiles)
    assert result["city"] == ["СПб", "Москва"]


def test_collect_suggestions_skips_none_and_empty():
    profiles = {
        "creative": {"city": None, "phone": "", "updated_at": datetime(2026, 5, 1, tzinfo=timezone.utc)},
        "event": {"city": "Москва", "phone": "+79991111111", "updated_at": datetime(2026, 5, 2, tzinfo=timezone.utc)},
    }
    result = _collect_suggestions(profiles)
    assert result["city"] == ["Москва"]
    assert result["phone"] == ["+79991111111"]


def test_collect_suggestions_skips_arrays_unless_canonical():
    """list[str] поля (project_types, work_types) не подсказываются — только скаляры."""
    profiles = {
        "creative": {"project_types": ["advertising"], "city": "Москва",
                     "updated_at": datetime(2026, 5, 1, tzinfo=timezone.utc)},
    }
    result = _collect_suggestions(profiles)
    assert "project_types" not in result
    assert result["city"] == ["Москва"]


def test_collect_suggestions_empty_profiles():
    assert _collect_suggestions({}) == {}
