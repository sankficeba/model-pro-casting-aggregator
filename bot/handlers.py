"""aiogram-бот: приветствие, ссылка на Mini App, админ-команды по каналам."""
from __future__ import annotations

import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardRemove
from loguru import logger

from config import settings
from db import repository

HELP_TEXT_USER = (
    "<b>Команды:</b>\n"
    "/start — приветствие\n"
    "/help — помощь"
)

HELP_TEXT_ADMIN = HELP_TEXT_USER + (
    "\n\n<b>Админ:</b>\n"
    "/channels — список каналов\n"
    "/addchannel @username — добавить канал\n"
    "/removechannel @username — отключить канал"
)

GREETING = (
    "Привет! Заполни анкету через кнопку Mini App рядом с полем ввода — "
    "после этого я начну присылать тебе подходящие объявления из "
    "отслеживаемых Telegram-каналов."
)


def _is_admin(user_id: int | None) -> bool:
    return user_id is not None and user_id in settings.admin_ids


def _help_for(user_id: int | None) -> str:
    return HELP_TEXT_ADMIN if _is_admin(user_id) else HELP_TEXT_USER


async def _restart_self(bot: Bot, message: Message, reason: str) -> None:
    """Отвечаем пользователю и перезапускаем процесс — docker compose поднимет
    нас обратно с обновлённым списком каналов из БД."""
    await message.answer(f"{reason}\nПерезапускаю userbot — каналы обновятся через ~10 секунд.")
    # Дать сообщению уйти в Telegram
    await asyncio.sleep(0.5)
    try:
        await bot.session.close()
    except Exception:  # noqa: BLE001
        pass
    logger.info("Restart requested by admin: {}", reason)
    os._exit(0)


def build_dispatcher(bot: Bot) -> Dispatcher:
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        await repository.upsert_user(
            message.from_user.id,
            username=message.from_user.username,
        )
        await message.answer(
            GREETING + "\n\n" + _help_for(message.from_user.id),
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )

    @dp.message(Command("help"))
    async def cmd_help(message: Message) -> None:
        await message.answer(_help_for(message.from_user.id), parse_mode="HTML")

    # ---------- Admin: channels ----------

    @dp.message(Command("channels"))
    async def cmd_channels(message: Message) -> None:
        if not _is_admin(message.from_user.id):
            return
        rows = await repository.list_channels(active_only=False)
        if not rows:
            await message.answer("Список каналов пуст.")
            return
        active = [r for r in rows if r.active]
        inactive = [r for r in rows if not r.active]
        lines = ["<b>Активные каналы:</b>"]
        lines += [f"• @{r.username}" for r in active] or ["—"]
        if inactive:
            lines += ["", "<i>Отключённые:</i>"] + [f"• @{r.username}" for r in inactive]
        await message.answer("\n".join(lines), parse_mode="HTML")

    @dp.message(Command("addchannel"))
    async def cmd_add_channel(message: Message) -> None:
        if not _is_admin(message.from_user.id):
            return
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await message.answer("Использование: <code>/addchannel @username</code>", parse_mode="HTML")
            return
        ch = await repository.add_channel(parts[1], added_by=message.from_user.id)
        if ch is None:
            await message.answer("Канал уже в активном списке.")
            return
        await _restart_self(bot, message, f"✅ Канал @{ch.username} добавлен.")

    @dp.message(Command("removechannel"))
    async def cmd_remove_channel(message: Message) -> None:
        if not _is_admin(message.from_user.id):
            return
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await message.answer(
                "Использование: <code>/removechannel @username</code>",
                parse_mode="HTML",
            )
            return
        removed = await repository.remove_channel(parts[1])
        if not removed:
            await message.answer("Такого активного канала не нашёл.")
            return
        await _restart_self(bot, message, "🗑 Канал отключён.")

    # ---------- Fallback ----------

    @dp.message(F.text)
    async def fallback(message: Message) -> None:
        await message.answer(
            "Не понял. " + _help_for(message.from_user.id),
            parse_mode="HTML",
        )

    return dp


async def run_bot(bot: Bot) -> None:
    dp = build_dispatcher(bot)
    logger.info("aiogram-бот запущен")
    await dp.start_polling(bot)
