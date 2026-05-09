"""Тарифы подписки. Хардкод — менять реже, чем 1 раз в квартал."""
from __future__ import annotations

from api.schemas import SubscriptionPlan


SUBSCRIPTION_PLANS: list[SubscriptionPlan] = [
    SubscriptionPlan(
        code="1m", days=30, price_rub=499,
        label="1 месяц", discount_pct=0, badge=None,
    ),
    SubscriptionPlan(
        code="3m", days=90, price_rub=1350,
        label="3 месяца", discount_pct=10, badge="Популярный",
    ),
    SubscriptionPlan(
        code="6m", days=180, price_rub=2550,
        label="6 месяцев", discount_pct=15, badge="Выгодный",
    ),
    SubscriptionPlan(
        code="12m", days=360, price_rub=4500,
        label="12 месяцев", discount_pct=25, badge="Максимум",
    ),
]


def get_plan(code: str | None) -> SubscriptionPlan:
    """Найти тариф по коду; если code не задан / неизвестен — вернуть 1m."""
    if code:
        for p in SUBSCRIPTION_PLANS:
            if p.code == code:
                return p
    return SUBSCRIPTION_PLANS[0]
