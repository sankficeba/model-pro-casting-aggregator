"""Telethon-userbot: слушает каналы, парсит сообщения через LLM,
рассылает совпадения подписчикам через aiogram-бота."""
from __future__ import annotations

import asyncio
from pathlib import Path

from aiogram import Bot
from loguru import logger
from telethon import TelegramClient, events

from config import settings
from filters.storage import FilterStorage
from llm.base import LLMProvider


class Userbot:
    def __init__(
        self,
        llm: LLMProvider,
        storage: FilterStorage,
        bot: Bot,
        session_dir: str | Path = "sessions",
    ):
        self.llm = llm
        self.storage = storage
        self.bot = bot
        Path(session_dir).mkdir(parents=True, exist_ok=True)
        self.client = TelegramClient(
            str(Path(session_dir) / settings.tg_session_name),
            settings.tg_api_id,
            settings.tg_api_hash,
        )

    async def _resolve_channels(self) -> list:
        entities = []
        for ch in settings.tg_channels:
            try:
                entity = await self.client.get_entity(ch)
                entities.append(entity)
                logger.info("Подписан на канал {} (id={})", ch, getattr(entity, "id", "?"))
            except Exception as e:  # noqa: BLE001
                logger.error("Не удалось получить entity для {}: {}", ch, e)
        return entities

    def _format_notification(self, data, message) -> str:
        link = ""
        try:
            if getattr(message.chat, "username", None):
                link = f"https://t.me/{message.chat.username}/{message.id}"
        except Exception:  # noqa: BLE001
            pass

        lines = [
            "<b>Найдена подходящая заявка</b>",
            f"Категория: {data.category or '-'}",
            f"Пол: {data.gender or '-'} | Возраст: {data.age if data.age is not None else '-'}",
            f"Уверенность: {data.confidence:.2f}",
            "",
            data.summary or (message.message or "")[:300],
        ]
        if link:
            lines.append(f"\n<a href=\"{link}\">Открыть сообщение</a>")
        return "\n".join(lines)

    async def _handle_message(self, event):
        text = (event.message.message or "").strip()
        if not text:
            return
        logger.debug("Новое сообщение: {!r}", text[:120])

        data = await self.llm.extract(text)
        if data.confidence == 0.0:
            return

        matches = await self.storage.find_matches(data)
        if not matches:
            return

        notification = self._format_notification(data, event.message)
        for f in matches:
            try:
                await self.bot.send_message(
                    f.user_id, notification, parse_mode="HTML", disable_web_page_preview=True
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("Не удалось отправить пользователю {}: {}", f.user_id, e)
            await asyncio.sleep(0.05)  # лёгкий троттлинг

    async def start(self) -> None:
        await self.client.start(phone=settings.tg_phone)
        entities = await self._resolve_channels()
        if not entities:
            logger.warning("Список каналов пуст или ни один не разрешился — userbot работает «вхолостую»")

        @self.client.on(events.NewMessage(chats=entities or None))
        async def _handler(event):  # noqa: ANN001
            await self._handle_message(event)

        logger.info("Userbot запущен, слушаю каналы: {}", settings.tg_channels)
        await self.client.run_until_disconnected()
