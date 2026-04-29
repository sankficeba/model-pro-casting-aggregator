"""aiogram-бот: приветствие + ссылка на Mini App."""
from __future__ import annotations

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardRemove
from loguru import logger

from db import repository

HELP_TEXT = (
    "<b>Команды:</b>\n"
    "/start — приветствие\n"
    "/help — помощь"
)

GREETING = (
    "Привет! Заполни анкету через кнопку Mini App рядом с полем ввода — "
    "после этого я начну присылать тебе подходящие объявления из "
    "отслеживаемых Telegram-каналов."
)


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        await repository.upsert_user(
            message.from_user.id,
            username=message.from_user.username,
        )
        await message.answer(
            GREETING + "\n\n" + HELP_TEXT,
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )

    @dp.message(Command("help"))
    async def cmd_help(message: Message) -> None:
        await message.answer(HELP_TEXT, parse_mode="HTML")

    @dp.message(F.text)
    async def fallback(message: Message) -> None:
        await message.answer("Не понял. " + HELP_TEXT, parse_mode="HTML")

    return dp


async def run_bot(bot: Bot) -> None:
    dp = build_dispatcher()
    logger.info("aiogram-бот запущен")
    await dp.start_polling(bot)
