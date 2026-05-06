"""Дедуп идентичных кастингов: нормализация текста + SHA-1.

Один и тот же пост, форварднутый в десятки каналов, должен давать
один хэш. Поэтому мы аккуратно убираем «чром» канала (forward-header,
эмодзи, t.me-ссылки, упоминания) и схлопываем whitespace перед
хэшированием.
"""
from __future__ import annotations

import hashlib
import re

# Forward-header в начале строки или после переноса. Telegram ставит
# его как «Forwarded from <name>\n».
_FORWARD_RE = re.compile(r"^Forwarded from .*?$", re.MULTILINE | re.IGNORECASE)

# Ссылки на t.me — частая «реклама себя» в подвале/шапке.
_TME_RE = re.compile(r"https?://t\.me/\S+", re.IGNORECASE)

# @username — упоминания администраторов/каналов. >=4 символа, чтобы
# не ломать обычные тексты с «@».
_MENTION_RE = re.compile(r"@[a-zA-Z0-9_]{4,}")

# Эмодзи. Покрываем основные диапазоны Unicode emoji + dingbats.
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F9FF"  # Misc symbols + emoticons + transport + sup symbols
    "\U0001FA00-\U0001FAFF"  # Symbols and pictographs extended-A
    "\U00002600-\U000027BF"  # Dingbats + misc symbols
    "\U0001F000-\U0001F02F"  # Mahjong/dominoes
    "\U0001F0A0-\U0001F0FF"  # Playing cards
    "‍"                 # Zero-width joiner (для составных эмодзи)
    "]+",
    flags=re.UNICODE,
)

_WHITESPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Канонизирует текст для дедупа: убирает Telegram-чром,
    эмодзи, упоминания, t.me-ссылки; схлопывает whitespace; casefold."""
    s = _FORWARD_RE.sub("", text)
    s = _TME_RE.sub("", s)
    s = _MENTION_RE.sub("", s)
    s = _EMOJI_RE.sub("", s)
    s = _WHITESPACE_RE.sub(" ", s).strip()
    return s.casefold()


def text_hash(text: str) -> str:
    """SHA-1 (hex) от нормализованного текста — стабильный fingerprint
    для дедупа форварднутых постов."""
    return hashlib.sha1(normalize(text).encode("utf-8")).hexdigest()
