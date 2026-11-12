"""Рекламный источник из /start <метка>: нормализация и first-touch."""
import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import insert as pg_insert

from db import repository as r
from db.models import User


@pytest.mark.parametrize("payload,expected", [
    ("vk_ads1", "vk_ads1"),
    ("VK_Ads-Nov", "vk_ads-nov"),
    ("  tg_post_12 ", "tg_post_12"),
    (None, None),
    ("", None),
    ("с кириллицей", None),
    ("a" * 65, None),
    ("bad$chars", None),
])
def test_normalize_source(payload, expected):
    assert r.normalize_source(payload) == expected


def test_conflict_update_does_not_touch_source():
    """Повторный /start обновляет username/last_active, но не source."""
    stmt = pg_insert(User).values(id=1, username="u", source="vk_ads1")
    stmt = stmt.on_conflict_do_update(
        index_elements=[User.id],
        set_={"username": "u", "last_active": stmt.excluded.last_active},
    )
    sql = str(stmt.compile(dialect=postgresql.dialect()))
    update_part = sql.split("DO UPDATE SET", 1)[1]
    assert "source" not in update_part
    assert "source" in sql.split("DO UPDATE SET", 1)[0]
