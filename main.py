"""Точка входа: одновременно поднимает Userbot (Telethon) и Bot (aiogram)."""
from __future__ import annotations

import asyncio
import sys

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from bot.handlers import run_bot
from config import settings
from db.session import dispose_engine
from filters.storage import FilterStorage
from llm.factory import get_llm_provider
from userbot.client import Userbot


def _setup_logging() -> None:
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level.upper())


async def main() -> None:
    _setup_logging()
    logger.info("Запуск приложения. LLM_PROVIDER={}", settings.llm_provider)

    storage = FilterStorage()
    llm = get_llm_provider()
    bot = Bot(
        settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    userbot = Userbot(llm=llm, storage=storage, bot=bot)

    try:
        await asyncio.gather(
            userbot.start(),
            run_bot(bot, storage),
        )
    finally:
        await bot.session.close()
        await dispose_engine()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановлено пользователем")
