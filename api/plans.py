"""Тарифы подписки. Хардкод — менять реже, чем 1 раз в квартал.

Базовая цена — 299 ₽/мес; скидка длинных тарифов считается от неё.
"""
from __future__ import annotations

from api.schemas import SubscriptionPlan

BASE_MONTHLY_PRICE_RUB = 299


def _plan(code: str, months: int, price_rub: int, label: str, badge: str | None) -> SubscriptionPlan:
    full = BASE_MONTHLY_PRICE_RUB * months
    discount = round((1 - price_rub / full) * 100) if price_rub < full else 0
    return SubscriptionPlan(
        code=code, days=30 * months, price_rub=price_rub,
        label=label, discount_pct=discount, badge=badge,
    )


SUBSCRIPTION_PLANS: list[SubscriptionPlan] = [
    _plan("1m", 1, 299, "1 месяц", None),
    _plan("3m", 3, 799, "3 месяца", "Популярный"),     # ≈ 266 ₽/мес, −11%
    _plan("6m", 6, 1490, "6 месяцев", "Выгодный"),     # ≈ 248 ₽/мес, −17%
    _plan("12m", 12, 2690, "12 месяцев", "Максимум"),  # ≈ 224 ₽/мес, −25%
]

PLAN_LABELS_EN = {"1m": "1 month", "3m": "3 months", "6m": "6 months", "12m": "12 months"}


def get_plan(code: str | None) -> SubscriptionPlan:
    """Найти тариф по коду; если code не задан / неизвестен — вернуть 1m."""
    if code:
        for p in SUBSCRIPTION_PLANS:
            if p.code == code:
                return p
    return SUBSCRIPTION_PLANS[0]


def find_plan(code: str | None) -> SubscriptionPlan | None:
    """Как get_plan, но без фолбэка: None для неизвестного кода."""
    return next((p for p in SUBSCRIPTION_PLANS if p.code == code), None)
