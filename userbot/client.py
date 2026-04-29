"""Telethon-userbot: слушает каналы, парсит сообщения через LLM,
пишет историю в БД и рассылает совпадения подходящим анкетам."""
from __future__ import annotations

import asyncio
from pathlib import Path

from aiogram import Bot
from loguru import logger
from telethon import TelegramClient, events

from api.reference_data import all_refs
from config import settings
from db import matching, repository
from llm.base import LLMProvider
from models.schemas import ExtractedData

# Сборка label-словарей для красивых названий в уведомлениях
_REFS = all_refs()
_PROJECT_LABELS = {it["code"]: it["label"] for it in _REFS["project_types"]}
_ROLE_LABELS = {it["code"]: it["label"] for it in _REFS["role_types"]}


def _labels(codes: list[str], mapping: dict[str, str]) -> str:
    if not codes:
        return "—"
    return ", ".join(mapping.get(c, c) for c in codes)


class Userbot:
    def __init__(
        self,
        llm: LLMProvider,
        bot: Bot,
        session_dir: str | Path = "sessions",
    ):
        self.llm = llm
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

        age_str = "—"
        if data.age_min is not None and data.age_max is not None:
            age_str = (
                f"{data.age_min}"
                if data.age_min == data.age_max
                else f"{data.age_min}–{data.age_max}"
            )
        elif data.age_min is not None:
            age_str = f"от {data.age_min}"
        elif data.age_max is not None:
            age_str = f"до {data.age_max}"

        gender_ru = {"male": "м", "female": "ж"}.get(data.gender or "", "—")
        rate_str = f"{data.rate} ₽" if data.rate is not None else "—"

        lines = [
            "<b>🎬 Подходящий кастинг</b>",
            f"Тип проекта: {_labels(data.project_types, _PROJECT_LABELS)}",
            f"Роль: {_labels(data.role_types, _ROLE_LABELS)}",
            f"Пол: {gender_ru} | Возраст: {age_str}",
            f"Город: {data.city or '—'} | Ставка: {rate_str}",
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
        logger.info(
            "LLM extract: casting={} gender={} age={}-{} project={} role={} city={} rate={} conf={:.2f}",
            data.is_casting,
            data.gender,
            data.age_min,
            data.age_max,
            data.project_types,
            data.role_types,
            data.city,
            data.rate,
            data.confidence,
        )

        # 2. История в БД (даже если is_casting=false — для дебага и аналитики)
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
        if message_db_id is None:
            return

        # 3. Подбор анкет
        user_ids = await matching.find_matching_profiles(data)
        if not user_ids:
            logger.debug("Нет подходящих анкет для сообщения {}", message_db_id)
            return

        notification_text = self._format_notification(data, event.message, chat_username)

        for user_id in user_ids:
            if await repository.already_notified(user_id, message_db_id):
                continue

            success = False
            err: str | None = None
            try:
                await self.bot.send_message(
                    user_id,
                    notification_text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
                success = True
            except Exception as e:  # noqa: BLE001
                err = str(e)
                logger.warning("Не удалось отправить пользователю {}: {}", user_id, e)

            await repository.log_notification(
                user_id=user_id,
                message_id=message_db_id,
                success=success,
                error=err,
            )
            await asyncio.sleep(0.05)  # лёгкий троттлинг

    async def start(self) -> None:
        await self.client.start(phone=settings.tg_phone)
        entities = await self._resolve_channels()
        if not entities:
            logger.warning(
                "Список каналов пуст или ни один не разрешился — userbot работает «вхолостую»"
            )

        @self.client.on(events.NewMessage(chats=entities or None))
        async def _handler(event):  # noqa: ANN001
            await self._handle_message(event)

        logger.info("Userbot запущен, слушаю каналы: {}", settings.tg_channels)
        await self.client.run_until_disconnected()
