"""Тесты dedup.normalize и dedup.text_hash."""
from __future__ import annotations

from db.dedup import normalize, text_hash


def test_normalize_strips_forward_header():
    raw = "Forwarded from Кастинг канал\nИщем актёра"
    assert "forwarded from" not in normalize(raw)
    assert "ищем актёра" in normalize(raw)


def test_normalize_strips_tme_links():
    raw = "Ищем актёра https://t.me/some_channel/123 на главную роль"
    out = normalize(raw)
    assert "t.me" not in out
    assert "ищем актёра" in out
    assert "на главную роль" in out


def test_normalize_strips_mentions():
    raw = "Подавайтесь @castingdir и подписывайтесь @kasting_oca"
    out = normalize(raw)
    assert "@castingdir" not in out
    assert "@kasting_oca" not in out
    assert "подавайтесь" in out
    assert "подписывайтесь" in out


def test_normalize_strips_emoji():
    raw = "🎬 Срочно! 🔥 Ищем актёра ✨"
    out = normalize(raw)
    assert "🎬" not in out
    assert "🔥" not in out
    assert "ищем актёра" in out


def test_normalize_collapses_whitespace():
    raw = "Ищем\n\n\nактёра  на     роль"
    out = normalize(raw)
    assert out == "ищем актёра на роль"


def test_normalize_casefolds_cyrillic():
    raw = "ИЩЕМ АКТЁРА"
    out = normalize(raw)
    assert out == "ищем актёра"


def test_text_hash_is_40_char_hex():
    h = text_hash("any text")
    assert len(h) == 40
    assert all(c in "0123456789abcdef" for c in h)


def test_text_hash_same_for_normalized_equivalents():
    """Главный тест: два варианта одного текста → один хэш.

    `forwarded` после strip'а forward-header, t.me-ссылок, упоминаний,
    эмодзи и нормализации whitespace должен дать ровно тот же текст,
    что и `canonical`.
    """
    canonical = "Ищем актёра на главную роль в фильм"
    forwarded = (
        "Forwarded from Кастинг канал\n\n"
        "🎬\n"
        "Ищем АКТЁРА на главную роль в фильм\n"
        "@castingdir\n"
        "https://t.me/some_casting_channel/123"
    )
    assert text_hash(canonical) == text_hash(forwarded)


def test_text_hash_differs_for_different_texts():
    a = "Ищем актёра на главную роль"
    b = "Ищем актрису на эпизод"
    assert text_hash(a) != text_hash(b)


def test_text_hash_handles_empty():
    """Пустой/whitespace-only текст не должен падать."""
    assert text_hash("") == text_hash("   \n\n  ")
