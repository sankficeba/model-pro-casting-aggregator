"""aiogram-бот: интерфейс пользователя для управления своим фильтром."""
from __future__ import annotations

import shlex

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from loguru import logger

from filters.storage import FilterStorage
from models.schemas import UserFilter

HELP_TEXT = (
    "<b>Команды:</b>\n"
    "/start — приветствие\n"
    "/help — помощь\n"
    "/filter — задать фильтр (см. формат ниже)\n"
    "/myfilter — показать текущий фильтр\n"
    "/delete — удалить фильтр\n\n"
    "<b>Формат /filter:</b>\n"
    "<code>/filter gender=female age=18-30 category=обучение confidence=0.6</code>\n"
    "Все параметры опциональны. Можно задать только часть.\n"
    "• gender: male | female\n"
    "• age: либо число, либо диапазон min-max\n"
    "• category: подстрока поиска по категории\n"
    "• confidence: минимальная уверенность 0..1 (по умолчанию 0.5)"
)


def _parse_filter_args(args: str, user_id: int) -> UserFilter:
    """Парсим строку вида 'gender=female age=18-30 category=обучение'."""
    kwargs: dict = {"user_id": user_id}
    if not args.strip():
        return UserFilter(**kwargs)

    for token in shlex.split(args):
        if "=" not in token:
            raise ValueError(f"Не понимаю параметр: {token!r}. Формат key=value.")
        key, value = token.split("=", 1)
        key = key.strip().lower()
        value = value.strip()

        if key == "gender":
            if value not in {"male", "female"}:
                raise ValueError("gender должен быть male или female")
            kwargs["target_gender"] = value
        elif key == "age":
            if "-" in value:
                a, b = value.split("-", 1)
                kwargs["min_age"] = int(a)
                kwargs["max_age"] = int(b)
            else:
                age = int(value)
                kwargs["min_age"] = age
                kwargs["max_age"] = age
        elif key == "category":
            kwargs["category"] = value
        elif key == "confidence":
            kwargs["min_confidence"] = float(value)
        else:
            raise ValueError(f"Неизвестный параметр: {key!r}")

    return UserFilter(**kwargs)


def _format_filter(f: UserFilter) -> str:
    age = "-"
    if f.min_age is not None or f.max_age is not None:
        age = f"{f.min_age or '*'}–{f.max_age or '*'}"
    return (
        "<b>Текущий фильтр:</b>\n"
        f"• Пол: {f.target_gender or '—'}\n"
        f"• Возраст: {age}\n"
        f"• Категория: {f.category or '—'}\n"
        f"• Мин. уверенность: {f.min_confidence:.2f}"
    )


def build_dispatcher(storage: FilterStorage) -> Dispatcher:
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        await message.answer(
            "Привет! Я уведомляю тебя о подходящих объявлениях из отслеживаемых "
            "Telegram-каналов.\n\n" + HELP_TEXT,
            parse_mode="HTML",
        )

    @dp.message(Command("help"))
    async def cmd_help(message: Message) -> None:
        await message.answer(HELP_TEXT, parse_mode="HTML")

    @dp.message(Command("filter"))
    async def cmd_filter(message: Message) -> None:
        # message.text вида: "/filter gender=female age=18-30"
        args = (message.text or "").partition(" ")[2]
        try:
            f = _parse_filter_args(args, user_id=message.from_user.id)
        except (ValueError, TypeError) as e:
            await message.answer(f"Ошибка: {e}\n\n{HELP_TEXT}", parse_mode="HTML")
            return

        await storage.upsert(f)
        logger.info("Пользователь {} обновил фильтр: {}", message.from_user.id, f)
        await message.answer("Фильтр сохранён.\n\n" + _format_filter(f), parse_mode="HTML")

    @dp.message(Command("myfilter"))
    async def cmd_my(message: Message) -> None:
        f = await storage.get(message.from_user.id)
        if not f:
            await message.answer("У тебя пока нет фильтра. Создай его через /filter.")
            return
        await message.answer(_format_filter(f), parse_mode="HTML")

    @dp.message(Command("delete"))
    async def cmd_delete(message: Message) -> None:
        ok = await storage.remove(message.from_user.id)
        await message.answer("Фильтр удалён." if ok else "У тебя и не было фильтра.")

    @dp.message(F.text)
    async def fallback(message: Message) -> None:
        await message.answer("Не понял. " + HELP_TEXT, parse_mode="HTML")

    return dp


async def run_bot(bot: Bot, storage: FilterStorage) -> None:
    dp = build_dispatcher(storage)
    logger.info("aiogram-бот запущен")
    await dp.start_polling(bot)
