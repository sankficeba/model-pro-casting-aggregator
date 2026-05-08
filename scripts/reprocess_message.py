"""Переразобрать одно сообщение по message_id: прогнать через LLM ещё раз,
обновить messages+vacancies, прогнать матчинг и разослать уведомления.

Используется для починки строк, которые в момент обработки попали под
старую логику и закрепились с is_casting=false. Дедуп нотификаций
обеспечивает UNIQUE(user_id, text_hash) — если кому-то уже уходило
по этому text_hash, дубль не отправится.

Пример:
    docker exec tg_parser_app python scripts/reprocess_message.py 8098
    docker exec tg_parser_app python scripts/reprocess_message.py 8098 --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiogram import Bot  # noqa: E402
from aiogram.client.default import DefaultBotProperties  # noqa: E402
from aiogram.enums import ParseMode  # noqa: E402
from loguru import logger  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402

from config import settings  # noqa: E402
from db.models import Message, Vacancy  # noqa: E402
from db.session import AsyncSessionLocal  # noqa: E402
from llm.factory import get_llm_provider  # noqa: E402
from userbot.client import Userbot  # noqa: E402


async def _resolve_canonical_id(message_id: int) -> int:
    """Если message_id — это duplicate, возвращает id его canonical.
    Иначе — сам message_id."""
    async with AsyncSessionLocal() as session:
        row = await session.execute(
            select(Message.id, Message.canonical_message_id).where(Message.id == message_id)
        )
        rec = row.one_or_none()
        if rec is None:
            raise SystemExit(f"messages.id={message_id} не найден")
        if rec.canonical_message_id is not None:
            logger.info(
                "message_id={} — duplicate; переключаемся на canonical={}",
                message_id, rec.canonical_message_id,
            )
            return rec.canonical_message_id
        return message_id


async def _load_message(message_id: int) -> Message:
    async with AsyncSessionLocal() as session:
        row = await session.execute(select(Message).where(Message.id == message_id))
        msg = row.scalar_one_or_none()
        if msg is None:
            raise SystemExit(f"messages.id={message_id} не найден")
        # detach: будем пользоваться вне сессии
        session.expunge(msg)
        return msg


async def _replace_extraction(message_id: int, extracted) -> list[int]:
    """Обновляет messages-row и пересоздаёт vacancies. Возвращает новые vacancy_ids."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            Message.__table__.update()
            .where(Message.id == message_id)
            .values(
                is_casting=extracted.is_casting,
                project_types=list(extracted.project_types),
                city=extracted.city,
                summary=extracted.summary,
                confidence=extracted.confidence,
                category=extracted.category,
            )
        )
        await session.execute(delete(Vacancy).where(Vacancy.message_id == message_id))

        vacancy_ids: list[int] = []
        if extracted.is_casting and extracted.vacancies:
            for idx, v in enumerate(extracted.vacancies):
                stmt = (
                    pg_insert(Vacancy)
                    .values(
                        message_id=message_id,
                        idx=idx,
                        role_types=list(v.role_types),
                        gender=v.gender,
                        age_min=v.age_min,
                        age_max=v.age_max,
                        rate=v.rate,
                        ethnicity=list(v.ethnicity),
                        height_min=v.height_min,
                        height_max=v.height_max,
                        body_type=list(v.body_type),
                        hair_color=list(v.hair_color),
                        hair_length=list(v.hair_length),
                        description=v.description,
                        role_label=v.role_label,
                        category=v.category,
                        work_types=list(v.work_types),
                    )
                    .returning(Vacancy.id)
                )
                res = await session.execute(stmt)
                vacancy_ids.append(res.scalar_one())

        await session.commit()
        return vacancy_ids


async def main() -> None:
    parser = argparse.ArgumentParser(description="Reprocess message via LLM + matching + notify")
    parser.add_argument("message_id", type=int, help="messages.id для переразбора")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="прогнать LLM и показать результат, но не писать в БД и не слать",
    )
    args = parser.parse_args()

    canonical_id = await _resolve_canonical_id(args.message_id)
    msg = await _load_message(canonical_id)

    logger.info(
        "Loaded message id={} chat={} tg_msg_id={} text_hash={}",
        msg.id, msg.tg_chat_username, msg.tg_message_id, msg.text_hash,
    )

    llm = get_llm_provider()
    extracted = await llm.extract(msg.text)
    logger.info(
        "LLM extract: casting={} category={} vacancies={} conf={:.2f}",
        extracted.is_casting, extracted.category,
        len(extracted.vacancies), extracted.confidence,
    )

    if args.dry_run:
        print(extracted.model_dump_json(indent=2))
        return

    if not extracted.is_casting or not extracted.vacancies:
        logger.warning(
            "LLM по-прежнему классифицирует это как не-кастинг — БД не трогаем",
        )
        return

    vacancy_ids = await _replace_extraction(canonical_id, extracted)
    logger.info("Replaced extraction: {} new vacancies inserted", len(vacancy_ids))

    bot = Bot(
        settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    fake_self = SimpleNamespace(
        bot=bot,
        _format_notification=Userbot._format_notification,
    )
    fake_message = SimpleNamespace(id=msg.tg_message_id, message=msg.text)

    try:
        await Userbot._process_canonical(
            fake_self,
            message_db_id=canonical_id,
            text_hash_value=msg.text_hash or "",
            post=extracted,
            vacancies=extracted.vacancies,
            vacancy_ids=vacancy_ids,
            message=fake_message,
            chat_username=msg.tg_chat_username,
        )
    finally:
        await bot.session.close()

    logger.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())
