"""Тарифы подписки.

Обычная цена — 499 ₽/мес (длинные тарифы со скидкой). До PROMO_UNTIL действует
акция: цены ниже, обычная показывается зачёркнутой. После даты акционные цены
отключаются сами — без деплоя.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from api.schemas import SubscriptionPlan

MSK = timezone(timedelta(hours=3))
BASE_MONTHLY_PRICE_RUB = 499

# Акция «до конца ноября»: действует до 01.12.2026 00:00 МСК.
# Можно переопределить env PROMO_UNTIL (ISO, например 2026-12-15T00:00:00+03:00)
# или выключить пустой строкой.
_promo_env = os.getenv("PROMO_UNTIL")
PROMO_UNTIL: datetime | None = (
    datetime(2026, 12, 1, tzinfo=MSK) if _promo_env is None
    else (datetime.fromisoformat(_promo_env) if _promo_env.strip() else None)
)

# (code, months, label, badge, regular_price, promo_price)
_PLANS = [
    ("1m", 1, "1 месяц", None, 499, 299),
    ("3m", 3, "3 месяца", "Популярный", 1350, 799),
    ("6m", 6, "6 месяцев", "Выгодный", 2550, 1490),
    ("12m", 12, "12 месяцев", "Максимум", 4500, 2690),
]

PLAN_LABELS_EN = {"1m": "1 month", "3m": "3 months", "6m": "6 months", "12m": "12 months"}


def promo_active(now: datetime | None = None) -> bool:
    return PROMO_UNTIL is not None and (now or datetime.now(timezone.utc)) < PROMO_UNTIL


def promo_last_day() -> datetime | None:
    """Последний день акции (для текста «до 30 ноября»)."""
    return (PROMO_UNTIL - timedelta(seconds=1)).astimezone(MSK) if PROMO_UNTIL else None


def current_plans(now: datetime | None = None) -> list[SubscriptionPlan]:
    """Тарифы с ценой, действующей сейчас."""
    promo = promo_active(now)
    out = []
    for code, months, label, badge, regular, promo_price in _PLANS:
        price = promo_price if promo else regular
        full = BASE_MONTHLY_PRICE_RUB * months
        out.append(SubscriptionPlan(
            code=code, days=30 * months, price_rub=price, label=label, badge=badge,
            discount_pct=round((1 - price / full) * 100) if price < full else 0,
            regular_price_rub=regular if promo and regular > price else None,
        ))
    return out


def get_plan(code: str | None, now: datetime | None = None) -> SubscriptionPlan:
    """Найти тариф по коду; если code не задан / неизвестен — вернуть 1m."""
    plans = current_plans(now)
    return next((p for p in plans if p.code == code), plans[0])


def find_plan(code: str | None, now: datetime | None = None) -> SubscriptionPlan | None:
    """Как get_plan, но без фолбэка: None для неизвестного кода."""
    return next((p for p in current_plans(now) if p.code == code), None)
