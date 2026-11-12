"""«Основная информация»: сборка из анкет, раскладка по анкетам, проценты."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from db import repository as r

NOW = datetime.now(timezone.utc)

BASE_OK = dict(
    full_name="Иван", gender="male", actual_age=21, city="Москва",
    phone="+79000000000", telegram_user="@ivan_p", email="i@e.ru",
)


def _row(**kw):
    data = dict(
        full_name=None, gender=None, actual_age=None, city=None, ready_for_travel=False,
        phone=None, telegram_user=None, vk_url=None, email=None, updated_at=NOW,
    )
    data.update(kw)
    return SimpleNamespace(**data)


def test_base_from_no_profiles_is_empty():
    b = r._base_from_profiles([])
    assert b["completed"] is False
    assert b["completion_pct"] == 0


def test_base_takes_freshest_value_and_fills_gaps_from_older():
    old = _row(**{**BASE_OK, "city": "Казань"}, ready_for_travel=True, updated_at=NOW - timedelta(days=5))
    new = _row(full_name="Иван Новый", city="Москва", updated_at=NOW)
    b = r._base_from_profiles([new, old])  # отсортированы: свежие первыми
    assert b["full_name"] == "Иван Новый"
    assert b["city"] == "Москва"
    assert b["phone"] == BASE_OK["phone"]  # пусто в свежей — берём из старой
    assert b["ready_for_travel"] is False  # флаг — из самой свежей анкеты
    assert b["completed"] is True and b["completion_pct"] == 100


def test_telegram_is_required_in_base():
    b = r._base_from_profiles([_row(**{**BASE_OK, "telegram_user": None})])
    assert b["completed"] is False


def test_missing_required_fields():
    prof = {**BASE_OK, "work_types": [], "min_rate": 0}
    assert r.missing_required_fields(prof, "general") == ["work_types"]
    prof["work_types"] = ["helper"]
    assert r.missing_required_fields(prof, "general") == []
    prof["phone"] = "  "
    assert r.missing_required_fields(prof, "general") == ["phone"]
    assert set(r.missing_required_fields(None, "creative")) == set(r._REQUIRED_FIELDS["creative"])


@pytest.mark.parametrize("category,extra,expected", [
    # Как в форме Mini App: основная информация — один пункт.
    ("creative", {}, 17),                                                     # 1/6
    ("creative", {"project_types": ["k"], "role_types": ["r"]}, 50),          # 3/6
    ("creative", {"project_types": ["k"], "role_types": ["r"], "play_age_min": 18,
                  "play_age_max": 25, "min_rate": 0}, 100),
    ("event", {"work_types": ["hostess"]}, 67),                                # 2/3
    ("general", {"work_types": ["helper"], "min_rate": 3000}, 100),
])
def test_completion_pct_matches_form(category, extra, expected):
    empty = dict(project_types=[], role_types=[], play_age_min=None, play_age_max=None,
                 min_rate=None, work_types=[])
    assert r._completion_pct(SimpleNamespace(**BASE_OK, **{**empty, **extra}), category) == expected


def test_completion_pct_rounds_half_up_like_js():
    # 1 из 8 = 12.5% → 13 (как Math.round во фронте), а не 12 (banker's).
    assert int(1 * 100 / 8 + 0.5) == 13


class _FakeRes:
    def __init__(self, q, subs, existing):
        self.q, self.subs, self.existing = str(q), subs, existing

    def scalars(self):
        return SimpleNamespace(all=lambda: list(self.subs))

    def first(self):
        table = self.q.split("FROM ")[1].split()[0]
        return (1,) if table in self.existing else None


class _FakeSession:
    def __init__(self, subs, existing):
        self.subs, self.existing = subs, existing

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def execute(self, q):
        return _FakeRes(q, self.subs, self.existing)


@pytest.mark.parametrize("subs,existing,expected_cats", [
    (["creative", "general"], {"admin_profile"}, ["admin", "creative", "general"]),
    ([], set(), ["general"]),  # новый юзер без направлений — черновик general
])
async def test_set_base_profile_fans_out_only_base_fields(monkeypatch, subs, existing, expected_cats):
    written = []

    async def fake_upsert(uid, cat, data):
        written.append((cat, dict(data)))

    async def fake_get(uid):
        return {}

    monkeypatch.setattr(r, "AsyncSessionLocal", lambda: _FakeSession(subs, existing))
    monkeypatch.setattr(r, "upsert_category_profile", fake_upsert)
    monkeypatch.setattr(r, "get_base_profile", fake_get)
    await r.set_base_profile(1, {"full_name": "X", "work_types": ["hack"], "city": "Y"})
    assert [c for c, _ in written] == expected_cats
    assert all(d == {"full_name": "X", "city": "Y"} for _, d in written)
