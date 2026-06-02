"""Точка входа: одновременно поднимает Userbot (Telethon) и Bot (aiogram)."""
from __future__ import annotations

import asyncio
import sys

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger

from bot.handlers import run_bot
from config import settings
from db import repository
from db.session import dispose_engine
from llm.factory import get_llm_provider
from userbot.client import Userbot


def _setup_logging() -> None:
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level.upper())


async def night_digest_loop(bot: Bot) -> None:
    """Раз в минуту проверяет юзеров с night-mode которые «проснулись»
    (текущий MSK-час == night_end_hour) и имеют pending. Шлёт им
    приглашение «За ночь — N объявлений, посмотреть?» с кнопкой Далее."""
    while True:
        try:
            await asyncio.sleep(60)
            users = await repository.list_users_with_pending_in_morning()
            for user_id, count in users:
                text = (
                    f"☀️ <b>Доброе утро!</b>\n\n"
                    f"За ночь было опубликовано <b>{count}</b> подходящих объявлений. "
                    f"Хочешь посмотреть?"
                )
                from bot.keyboards import EMOJI_NEXT
                kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="следующая вакансия",
                        callback_data="digest:next",
                        icon_custom_emoji_id=EMOJI_NEXT,
                    )
                ]])
                try:
                    await bot.send_message(
                        user_id, text, parse_mode="HTML", reply_markup=kb
                    )
                    await repository.mark_night_digest_sent(user_id)
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "Morning digest send failed for {}: {}", user_id, e,
                    )
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.exception("night_digest_loop error: {}", e)


async def expiry_reminder_loop(bot: Bot) -> None:
    """Раз в 5 минут шлёт юзерам напоминалки об истечении подписки на стадиях
    2 суток / 1 сутки / 3 часа до конца. Каждая стадия отправляется один раз."""
    stage_labels = {
        "2d": ("⏳ Подписка истекает через 2 дня", "2 дня"),
        "1d": ("⏳ Подписка истекает завтра", "1 день"),
        "3h": ("⚠️ Подписка истекает через 3 часа", "3 часа"),
    }
    while True:
        try:
            await asyncio.sleep(300)
            for stage in ("2d", "1d", "3h"):
                users = await repository.list_users_for_expiry_reminder(stage)
                title, friendly = stage_labels[stage]
                for user_id, active_until in users:
                    text = (
                        f"<b>{title}</b>\n\n"
                        f"Активна до <b>{active_until.strftime('%d.%m.%Y %H:%M МСК')}</b> "
                        f"(осталось примерно {friendly}).\n\n"
                        "Продли подписку в Mini App, чтобы продолжить получать "
                        "уведомления о кастингах без задержек."
                    )
                    try:
                        await bot.send_message(user_id, text, parse_mode="HTML")
                        await repository.mark_expiry_reminder_sent(user_id, stage)
                    except Exception as e:  # noqa: BLE001
                        logger.warning(
                            "Expiry reminder send failed user={} stage={}: {}",
                            user_id, stage, e,
                        )
                    await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.exception("expiry_reminder_loop error: {}", e)


async def daily_digest_loop(bot: Bot) -> None:
    """Раз в минуту проверяет юзеров digest-режима с включённой ежедневной
    плашкой: текущий MSK-час == digest_daily_hour, есть pending, сегодня
    ещё не слали. Отправляет «За сегодня — N объявлений, посмотреть?»."""
    while True:
        try:
            await asyncio.sleep(60)
            users = await repository.list_users_for_daily_digest_due()
            for user_id, count in users:
                text = (
                    f"📬 <b>Накопленные объявления</b>\n\n"
                    f"За сегодня — <b>{count}</b> подходящих кастингов. "
                    f"Хочешь посмотреть?"
                )
                from bot.keyboards import EMOJI_NEXT
                kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="следующая вакансия",
                        callback_data="digest:next",
                        icon_custom_emoji_id=EMOJI_NEXT,
                    )
                ]])
                try:
                    await bot.send_message(
                        user_id, text, parse_mode="HTML", reply_markup=kb
                    )
                    await repository.mark_daily_digest_sent(user_id)
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "Daily digest send failed for {}: {}", user_id, e,
                    )
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.exception("daily_digest_loop error: {}", e)


async def main() -> None:
    _setup_logging()
    logger.info("Запуск приложения. LLM_PROVIDER={}", settings.llm_provider)

    llm = get_llm_provider()
    bot = Bot(
        settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    userbot = Userbot(llm=llm, bot=bot)

    try:
        await asyncio.gather(
            userbot.start(),
            run_bot(bot, llm=llm, userbot=userbot),
            night_digest_loop(bot),
            daily_digest_loop(bot),
            expiry_reminder_loop(bot),
            userbot._llm_retry_loop(),
        )
    finally:
        await bot.session.close()
        await dispose_engine()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановлено пользователем")
