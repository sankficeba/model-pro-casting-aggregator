"""Telethon-userbot: слушает каналы, парсит сообщения через LLM,
пишет историю в БД и рассылает совпадения подписчикам через aiogram-бота."""
from __future__ import annotations

import asyncio
from pathlib import Path

from aiogram import Bot
from loguru import logger
from telethon import TelegramClient, events

from config import settings
from db import repository
from filters.storage import FilterStorage
from llm.base import LLMProvider
from models.schemas import ExtractedData


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

    @staticmethod
    def _format_notification(data: ExtractedData, message, chat_username: str | None) -> str:
        link = ""
        if chat_username:
            link = f"https://t.me/{chat_username}/{message.id}"

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

        # 1. Парсинг через LLM
        data = await self.llm.extract(text)
        logger.debug("Extracted: {}", data.model_dump())

        # 2. Сохраняем сообщение в БД (даже если confidence низкая — для истории)
        chat = event.message.chat
        chat_id = getattr(chat, "id", 0)
        chat_username = getattr(chat, "username", None)
        message_db_id = await repository.insert_message(
            tg_chat_id=chat_id,
            tg_chat_username=chat_username,
            tg_message_id=event.message.id,
            text=text,
            extracted=data,
        )

        # Слишком низкая уверенность — не рассылаем
        if data.confidence == 0.0 or message_db_id is None:
            return

        # 3. Подбираем фильтры
        matches = await self.storage.find_matches(data)
        if not matches:
            return

        # Получаем фильтры с их БД-id, чтобы записать в notifications
        from db.models import Filter
        from sqlalchemy import select
        from db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Filter))
            filter_rows = {f.user_id: f.id for f in res.scalars().all()}

        notification_text = self._format_notification(data, event.message, chat_username)

        for f in matches:
            # Дедуп: если уже отправляли — пропустить
            if await repository.already_notified(f.user_id, message_db_id):
                continue

            success = False
            err: str | None = None
            try:
                await self.bot.send_message(
                    f.user_id,
                    notification_text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
                success = True
            except Exception as e:  # noqa: BLE001
                err = str(e)
                logger.warning("Не удалось отправить пользователю {}: {}", f.user_id, e)

            filter_id = filter_rows.get(f.user_id)
            if filter_id is not None:
                await repository.log_notification(
                    user_id=f.user_id,
                    message_id=message_db_id,
                    filter_id=filter_id,
                    success=success,
                    error=err,
                )
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
