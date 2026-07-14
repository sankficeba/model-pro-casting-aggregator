"""Минимальная i18n-прослойка для бота: только ru/en, без внешних
зависимостей. Каждая пользовательская строка задаётся инлайн через t(),
без реестра ключей — проще ревьюить и не даёт разъехаться переводам."""
from __future__ import annotations

from db import repository

Lang = str  # "ru" | "en"


def resolve_lang(telegram_language_code: str | None, override: str | None) -> Lang:
    """override — явный выбор юзера через /language (приоритетнее). Иначе
    auto-detect: en-* клиенты Telegram получают английский, все
    остальные (включая отсутствие кода) — русский, как и раньше."""
    if override in ("ru", "en"):
        return override
    if (telegram_language_code or "").lower().startswith("en"):
        return "en"
    return "ru"


async def get_lang(user_id: int, telegram_language_code: str | None) -> Lang:
    override = await repository.get_user_language(user_id)
    return resolve_lang(telegram_language_code, override)


def t(lang: Lang, ru: str, en: str) -> str:
    return en if lang == "en" else ru
