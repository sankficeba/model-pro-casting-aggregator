"""Разбор callback_data кнопок «Добавить/Не добавлять» под предложением канала."""
from bot.handlers import parse_suggestion_callback


def test_new_format_with_suggester_id():
    assert parse_suggestion_callback("csg:add:123456789:kastingi_msk") == ("add", 123456789, "kastingi_msk")


def test_new_format_private_and_invite_refs():
    assert parse_suggestion_callback("csg:skip:42:c/1968214811") == ("skip", 42, "c/1968214811")
    assert parse_suggestion_callback("csg:add:42:+AbCdEf123") == ("add", 42, "+AbCdEf123")


def test_legacy_format_without_suggester():
    assert parse_suggestion_callback("csg:add:kastingi_msk") == ("add", None, "kastingi_msk")
    assert parse_suggestion_callback("csg:add:c/1968214811") == ("add", None, "c/1968214811")


def test_broken_callbacks():
    assert parse_suggestion_callback("csg:add") is None
    assert parse_suggestion_callback("csg:add:") is None
    assert parse_suggestion_callback("csg:add:42:") is None
    assert parse_suggestion_callback("xyz:add:foo") is None


def test_callback_fits_telegram_limit():
    """Самый длинный username (32) + большой user id укладываются в 64 байта."""
    uid = 99999999999
    ref = "a" * 32
    prefix_len = len(f"csg:skip:{uid}:")
    data = f"csg:skip:{uid}:{ref[:64 - prefix_len]}"
    assert len(data.encode()) <= 64
    assert parse_suggestion_callback(data) == ("skip", uid, ref)
