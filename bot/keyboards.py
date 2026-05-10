"""Общие билдеры inline-клавиатур для бота и userbot'а."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton

# Premium custom-emoji icons для inline-кнопок (Bot API 9.4 +
# `icon_custom_emoji_id`). У владельца бота должен быть подключён
# Telegram Premium, иначе клиенты молча пропустят поле и покажут
# текст без иконки.
EMOJI_RESPOND = "5445190951259612625"   # 📩
EMOJI_DETAILS = "5778351117733729026"   # 🔗
EMOJI_DELETE = "5019500511871632068"    # 🗑
EMOJI_FAV_ADD = "5361760588764566472"   # 📎
EMOJI_FAV_REMOVE = "5465665476971471368"  # ❌


def actions_rows(*, message_id: int, is_favorited: bool) -> list[list[InlineKeyboardButton]]:
    """3 кнопки под каждым кастинг-уведомлением: ссылка на канал,
    удалить сообщение, добавить/убрать из избранного.

    Возвращает 2 ряда:
      [Подробнее] [Удалить]
      [В избранное / Удалить из избранного]
    """
    fav_btn = (
        InlineKeyboardButton(
            text="Удалить из избранного",
            callback_data=f"fav:rm:{message_id}",
            icon_custom_emoji_id=EMOJI_FAV_REMOVE,
        )
        if is_favorited
        else InlineKeyboardButton(
            text="Добавить в избранное",
            callback_data=f"fav:add:{message_id}",
            icon_custom_emoji_id=EMOJI_FAV_ADD,
        )
    )
    return [
        [
            InlineKeyboardButton(
                text="Ссылка на сообщение",
                callback_data=f"details:{message_id}",
                icon_custom_emoji_id=EMOJI_DETAILS,
            ),
            InlineKeyboardButton(
                text="Удалить",
                callback_data="delself:",
                icon_custom_emoji_id=EMOJI_DELETE,
            ),
        ],
        [fav_btn],
    ]


def problem_resolve_row(problem_id: int) -> list[list[InlineKeyboardButton]]:
    """Кнопка под админ-уведомлением о новой проблеме: «Проблема решена»
    закрывает тикет и редактирует исходное сообщение в чате."""
    return [[
        InlineKeyboardButton(
            text="✅ Проблема решена",
            callback_data=f"problem:resolve:{problem_id}",
        ),
    ]]


def problem_resolve_dict(problem_id: int) -> dict:
    """Тот же ряд, но в виде dict для отправки через httpx (FastAPI)."""
    return {
        "inline_keyboard": [[
            {"text": "✅ Проблема решена",
             "callback_data": f"problem:resolve:{problem_id}"},
        ]]
    }
