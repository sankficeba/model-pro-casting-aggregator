"""Подтянуть статусы всех pending-платежей из YooKassa и применить их.

Используется как fallback если webhook не дошёл (например URL вебхука
не настроен в ЛК YooKassa). Безопасно гонять сколько угодно — продление
идёт через mark_payment_status, который идемпотентен.

Пример:
    docker exec tg_parser_api python scripts/sync_pending_payments.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger  # noqa: E402
from sqlalchemy import select  # noqa: E402

from db import repository as repo  # noqa: E402
from db.models import Payment  # noqa: E402
from db.session import AsyncSessionLocal  # noqa: E402
from payments import yookassa_client  # noqa: E402


async def list_pending() -> list[Payment]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Payment)
            .where(Payment.status == "pending")
            .where(Payment.yk_payment_id.is_not(None))
            .order_by(Payment.id.asc())
        )
        rows = list(res.scalars().all())
        for r in rows:
            session.expunge(r)
        return rows


def fetch_payment_status(yk_id: str) -> dict | None:
    """Синхронный вызов YooKassa Payment.find_one — обёртка ниже зовёт через to_thread."""
    if not yookassa_client.is_configured():
        raise RuntimeError("YooKassa не настроена")
    from yookassa import Configuration, Payment as YkPayment

    Configuration.account_id  # type: ignore[attr-defined]
    yookassa_client._configure()  # noqa: SLF001
    p = YkPayment.find_one(yk_id)
    return {
        "id": p.id,
        "status": p.status,
        "paid": p.paid,
    }


async def main() -> None:
    if not yookassa_client.is_configured():
        print("YooKassa не настроена — нечего проверять.")
        return
    pending = await list_pending()
    if not pending:
        print("Pending-платежей нет.")
        return
    print(f"Pending платежей: {len(pending)}")
    for p in pending:
        try:
            info = await asyncio.to_thread(fetch_payment_status, p.yk_payment_id)
        except Exception as e:  # noqa: BLE001
            logger.warning("YK find_one failed for {}: {}", p.yk_payment_id, e)
            continue
        print(
            f"  payment id={p.id} user={p.user_id} yk={p.yk_payment_id} "
            f"db_status={p.status} yk_status={info['status']}"
        )
        new_status = info["status"]
        if new_status not in ("succeeded", "canceled"):
            continue
        should_extend = await repo.mark_payment_status(p.yk_payment_id, new_status)
        if should_extend:
            new_until = await repo.extend_subscription(p.user_id, p.days)
            print(
                f"  → продлили подписку user={p.user_id} до {new_until.isoformat()}"
            )


if __name__ == "__main__":
    asyncio.run(main())
