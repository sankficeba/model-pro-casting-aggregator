"""Сбор ссылок из поста (скрытые text-url, url в тексте, URL-кнопки)."""
from types import SimpleNamespace

from telethon.tl.types import MessageEntityBold, MessageEntityTextUrl, MessageEntityUrl

from userbot.client import extract_links


def _msg(entities_text=(), rows=()):
    return SimpleNamespace(
        get_entities_text=lambda: list(entities_text),
        reply_markup=SimpleNamespace(rows=[SimpleNamespace(buttons=list(r)) for r in rows]) if rows else None,
    )


def test_collects_text_urls_plain_urls_and_buttons_without_duplicates():
    m = _msg(
        entities_text=[
            (MessageEntityTextUrl(0, 8, url="https://h1.nu/abc"), "Оригинал"),
            (MessageEntityUrl(10, 20, ), "https://t.me/chan/1"),
            (MessageEntityBold(0, 3), "Жир"),
            (MessageEntityTextUrl(0, 3, url="https://h1.nu/abc"), "дубль"),
        ],
        rows=[[SimpleNamespace(text="👁 Подробнее", url="https://t.me/Bot?start=x"),
               SimpleNamespace(text="callback", data=b"x")]],
    )
    assert extract_links(m) == ["https://h1.nu/abc", "https://t.me/chan/1", "https://t.me/Bot?start=x"]


def test_no_links():
    assert extract_links(_msg()) == []


def test_never_raises_on_broken_message():
    class Broken:
        def get_entities_text(self):
            raise RuntimeError("boom")

    assert extract_links(Broken()) == []


def test_caps_count():
    many = [(MessageEntityTextUrl(0, 1, url=f"https://x.ru/{i}"), "x") for i in range(100)]
    assert len(extract_links(_msg(entities_text=many))) == 30
