"""Создание платежа за подписку — общее для Mini App (API) и бота.

Продление подписки делает webhook ЮKassa (api/main.py: yookassa_webhook)
по записи в payments, поэтому источник платежа ему безразличен.
"""
from __future__ import annotations

import uuid

from api.schemas import SubscriptionPlan
from config import settings
from db import repository as repo
from payments import yookassa_client
from payments.yookassa_client import CreatedPayment


async def create_subscription_payment(user_id: int, plan: SubscriptionPlan) -> CreatedPayment:
    """Записать pending-платёж и создать его в ЮKassa. Бросает исключение,
    если ЮKassa не настроена или вернула ошибку."""
    idempotency_key = uuid.uuid4().hex
    payment_id = await repo.insert_payment_pending(
        user_id=user_id,
        idempotency_key=idempotency_key,
        amount_rub=plan.price_rub,
        days=plan.days,
    )
    base_return = settings.subscription_return_url or "https://t.me/"
    # Маркер ?paid=1 нужен чтобы Mini App после редиректа понял, что юзер
    # только что оплатил и показал toast «Подписка активирована».
    sep = "&" if "?" in base_return else "?"
    created = await yookassa_client.create_payment(
        amount_rub=plan.price_rub,
        days=plan.days,
        user_id=user_id,
        idempotency_key=idempotency_key,
        return_url=f"{base_return}{sep}paid=1",
        description=f"Подписка: {plan.label}",
    )
    await repo.attach_yk_payment_id(payment_id, created.payment_id)
    return created
