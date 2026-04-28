"""Валидация Telegram WebApp initData по HMAC-SHA256.

Документация: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException, status

from config import settings


@dataclass
class TelegramUser:
    id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    language_code: Optional[str]
    is_premium: bool = False


# Допустимая «свежесть» initData. По умолчанию Telegram советует 24 часа.
INIT_DATA_MAX_AGE_SEC = 24 * 60 * 60


def _check_signature(init_data: str, bot_token: str) -> dict[str, str]:
    """Парсит initData строку и проверяет HMAC. Возвращает словарь параметров."""
    pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="initData: hash отсутствует"
        )

    # Собираем data_check_string: ключи отсортированы, формат key=value через \n
    data_check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs.keys()))
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256
    ).digest()
    calc_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calc_hash, received_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="initData: неверная подпись"
        )

    # Проверяем срок жизни
    auth_date = int(pairs.get("auth_date", "0") or 0)
    if auth_date and (time.time() - auth_date) > INIT_DATA_MAX_AGE_SEC:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="initData: устарела"
        )

    return pairs


def parse_init_data(init_data: str) -> TelegramUser:
    """Полная валидация + извлечение пользователя."""
    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="initData отсутствует"
        )
    pairs = _check_signature(init_data, settings.bot_token)

    user_raw = pairs.get("user")
    if not user_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="initData: нет user"
        )
    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"initData.user не парсится: {e}"
        ) from e

    return TelegramUser(
        id=int(user["id"]),
        username=user.get("username"),
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        language_code=user.get("language_code"),
        is_premium=bool(user.get("is_premium", False)),
    )


# --- FastAPI Dependency ---

async def current_user(
    x_telegram_init_data: str = Header(
        ..., alias="X-Telegram-Init-Data", description="window.Telegram.WebApp.initData"
    ),
) -> TelegramUser:
    """Зависимость: фронт обязан слать initData в заголовке X-Telegram-Init-Data."""
    return parse_init_data(x_telegram_init_data)
