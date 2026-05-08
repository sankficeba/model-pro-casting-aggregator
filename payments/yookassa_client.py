"""Тонкая обёртка над YooKassa SDK.

SDK синхронный, поэтому методы создания платежа гоняем через
asyncio.to_thread, чтобы не блокировать event loop API.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Optional

from loguru import logger

from config import settings


@dataclass
class CreatedPayment:
    payment_id: str
    confirmation_url: str
    status: str


def is_configured() -> bool:
    return bool(settings.yookassa_shop_id and settings.yookassa_secret_key)


def _configure() -> None:
    """Идемпотентно проставляем глобальную конфигу YooKassa SDK."""
    from yookassa import Configuration

    Configuration.account_id = settings.yookassa_shop_id
    Configuration.secret_key = settings.yookassa_secret_key


async def create_payment(
    *,
    amount_rub: int,
    days: int,
    user_id: int,
    idempotency_key: str,
    return_url: str,
    description: str,
) -> CreatedPayment:
    if not is_configured():
        raise RuntimeError("YooKassa не настроена (нет SHOP_ID/SECRET_KEY).")

    def _sync() -> CreatedPayment:
        _configure()
        from yookassa import Payment as YkPayment

        payment = YkPayment.create(
            {
                "amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url,
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "user_id": str(user_id),
                    "days": str(days),
                },
            },
            idempotency_key,
        )
        return CreatedPayment(
            payment_id=payment.id,
            confirmation_url=payment.confirmation.confirmation_url,
            status=payment.status,
        )

    return await asyncio.to_thread(_sync)


def parse_webhook(body_bytes: bytes) -> Optional[dict]:
    """Распарсить webhook payload в dict с {event, payment_id, status, metadata}.
    Возвращает None если payload невалиден или не payment-event."""
    try:
        from yookassa.domain.notification import WebhookNotification

        data = json.loads(body_bytes.decode("utf-8"))
        notification = WebhookNotification(data)
        obj = notification.object  # PaymentResponse / RefundResponse
        return {
            "event": notification.event,
            "payment_id": getattr(obj, "id", None),
            "status": getattr(obj, "status", None),
            "metadata": dict(getattr(obj, "metadata", {}) or {}),
        }
    except Exception as e:  # noqa: BLE001
        logger.warning("YooKassa webhook parse failed: {}", e)
        return None
