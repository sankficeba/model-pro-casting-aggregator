"""Общие билдеры inline-клавиатур для бота и userbot'а."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton


def actions_rows(*, message_id: int, is_favorited: bool) -> list[list[InlineKeyboardButton]]:
    """3 кнопки под каждым кастинг-уведомлением: ссылка на канал,
    удалить сообщение, добавить/убрать из избранного.

    Возвращает 2 ряда:
      [Подробнее] [Удалить]
      [В избранное / Удалить из избранного]
    """
    fav_btn = (
        InlineKeyboardButton(
            text="🗂 Удалить из избранного",
            callback_data=f"fav:rm:{message_id}",
        )
        if is_favorited
        else InlineKeyboardButton(
            text="🎟 Добавить в избранное",
            callback_data=f"fav:add:{message_id}",
        )
    )
    return [
        [
            InlineKeyboardButton(
                text="🔗 Подробнее",
                callback_data=f"details:{message_id}",
            ),
            InlineKeyboardButton(
                text="❌ Удалить",
                callback_data="delself:",
            ),
        ],
        [fav_btn],
    ]
