"""Telethon-userbot: слушает каналы, парсит сообщения через LLM,
пишет историю в БД и рассылает совпадения подходящим анкетам."""
from __future__ import annotations

import asyncio
from pathlib import Path

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger
from telethon import TelegramClient, events
from telethon.errors import (
    ChannelPrivateError,
    InviteHashExpiredError,
    UserAlreadyParticipantError,
)
from telethon.tl.functions.channels import JoinChannelRequest

from api.reference_data import all_refs
from config import settings
from db import matching, repository
from db.dedup import text_hash
from llm.base import LLMProvider
from models.schemas import PostExtraction, VacancyExtraction

_REFS = all_refs()
_PROJECT_LABELS = {it["code"]: it["label"] for it in _REFS["project_types"]}
_ROLE_LABELS = {it["code"]: it["label"] for it in _REFS["role_types"]}


def _labels(codes: list[str], mapping: dict[str, str]) -> str:
    if not codes:
        return "—"
    return ", ".join(mapping.get(c, c) for c in codes)


def _format_age(v: VacancyExtraction) -> str:
    if v.age_min is not None and v.age_max is not None:
        return f"{v.age_min}" if v.age_min == v.age_max else f"{v.age_min}–{v.age_max}"
    if v.age_min is not None:
        return f"от {v.age_min}"
    if v.age_max is not None:
        return f"до {v.age_max}"
    return "—"


def _vacancy_title(v: VacancyExtraction) -> str:
    """role_label если есть → русский label из справочника → 'Роль'."""
    if v.role_label:
        return v.role_label
    if v.role_types:
        return _ROLE_LABELS.get(v.role_types[0], v.role_types[0])
    return "Роль"


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
        await repository.seed_channels_if_empty(settings.tg_channels, added_by=0)
        rows = await repository.list_channels(active_only=True)

        if not rows:
            logger.warning("Нет активных каналов в БД — userbot работает «вхолостую»")
            return []

        entities = []
        for row in rows:
            # Какой ссылкой адресуем канал — публичный username или
            # приватный chat_id (t.me/c/<id> → -100<id> в БД).
            if row.tg_chat_id is not None:
                ref_for_log = f"id={row.tg_chat_id}"
                ref_for_get = row.tg_chat_id
                is_private = True
            else:
                ref_for_log = f"@{row.username}"
                ref_for_get = f"@{row.username}"
                is_private = False

            try:
                entity = await self.client.get_entity(ref_for_get)
            except Exception as e:  # noqa: BLE001
                logger.error("Не удалось получить entity для {}: {}", ref_for_log, e)
                continue

            # Для приватных каналов аккаунт уже должен быть в них —
            # вступить через JoinChannelRequest нельзя без invite-hash.
            if is_private:
                logger.info("Слушаю приватный канал {} (entity id={})",
                            ref_for_log, getattr(entity, "id", "?"))
                entities.append(entity)
                continue

            # Публичный канал: get_entity только резолвит, не вступает.
            # Дёргаем JoinChannelRequest идемпотентно (best-effort) — если
            # упало (FloodWait/pending-approval/прочее), всё равно подключаем
            # entity к фильтру Telethon: аккаунт мог уже быть участником с
            # прошлых рестартов, и тогда NewMessage всё равно дойдут.
            try:
                await self.client(JoinChannelRequest(entity))
                logger.info("Вступил в канал {} (id={})", ref_for_log, getattr(entity, "id", "?"))
            except UserAlreadyParticipantError:
                logger.info("Уже состою в канале {} (id={})", ref_for_log, getattr(entity, "id", "?"))
            except (ChannelPrivateError, InviteHashExpiredError) as e:
                # Канал реально недоступен — entity бесполезен.
                logger.warning("Канал {} недоступен ({}); событий не будет", ref_for_log, type(e).__name__)
                continue
            except Exception as e:  # noqa: BLE001
                # FloodWait и т.п. — не критично, entity всё равно слушаем.
                logger.warning("JoinChannelRequest для {} не прошёл ({}); продолжаем слушать", ref_for_log, e)

            entities.append(entity)
        return entities

    @staticmethod
    def _format_notification(
        *,
        post: PostExtraction,
        vacancies: list[VacancyExtraction],
        matched_idxs: list[int],
        message,
        chat_username: str | None,
    ) -> str:
        """Карточка для пользователя. Перечисляет только подошедшие вакансии."""
        link = ""
        if chat_username:
            link = f"https://t.me/{chat_username}/{message.id}"

        lines: list[str] = [
            "<b>🎬 Подходящий кастинг</b>",
            f"Тип проекта: {_labels(post.project_types, _PROJECT_LABELS)} | "
            f"Город: {post.city or '—'}",
            f"<b>Подходящие роли ({len(matched_idxs)}):</b>",
        ]
        for idx in matched_idxs:
            v = vacancies[idx]
            gender_ru = {"male": "м", "female": "ж"}.get(v.gender or "", "—")
            rate_str = f"{v.rate} ₽" if v.rate is not None else "ставка не указана"
            extras: list[str] = []
            if v.height_min is not None or v.height_max is not None:
                lo = v.height_min if v.height_min is not None else ""
                hi = v.height_max if v.height_max is not None else ""
                if lo and hi and lo != hi:
                    extras.append(f"рост {lo}–{hi} см")
                elif lo and hi and lo == hi:
                    extras.append(f"рост {lo} см")
                elif lo:
                    extras.append(f"рост от {lo} см")
                elif hi:
                    extras.append(f"рост до {hi} см")
            if v.ethnicity:
                extras.append(", ".join(v.ethnicity))
            extras_str = (" · " + " · ".join(extras)) if extras else ""
            lines.append(
                f"• <b>{_vacancy_title(v)}</b> — {_format_age(v)}, {gender_ru}, {rate_str}{extras_str}"
            )

        lines.append("")
        lines.append(post.summary or (message.message or "")[:300])
        if link:
            lines.append(f"\n<a href=\"{link}\">Открыть сообщение</a>")
        return "\n".join(lines)

    async def _process_canonical(
        self,
        *,
        message_db_id: int,
        text_hash_value: str,
        post: PostExtraction,
        vacancies: list[VacancyExtraction],
        vacancy_ids: list[int],
        message,  # noqa: ANN001 — Telethon Message
        chat_username: str | None,
    ) -> None:
        """Общий путь матчинга и рассылки. Вызывается:
        - На свежий canonical (после успешного insert_message_with_vacancies).
        - На duplicate-прилёт (после insert_duplicate_message + загрузки
          canonical-вакансий через get_canonical_with_vacancies).

        text_hash_value пробрасывается в log_notification → UNIQUE
        (user_id, text_hash) гарантирует «один кастинг = одно уведомление
        на юзера за всю историю».
        """
        if not post.is_casting or not vacancy_ids or not vacancies:
            return

        user_to_idxs = await matching.find_matching_vacancies(post, vacancies)
        if not user_to_idxs:
            logger.debug("Нет подходящих анкет для сообщения {}", message_db_id)
            return

        for user_id, hit_idxs in user_to_idxs.items():
            matched_db_ids = [vacancy_ids[i] for i in hit_idxs if i < len(vacancy_ids)]
            if not matched_db_ids:
                logger.warning(
                    "Skip notify user={} msg={}: vacancy_ids len mismatch "
                    "(db={}, extracted={})",
                    user_id, message_db_id, len(vacancy_ids), len(vacancies),
                )
                continue

            # Оптимистично пишем нотификацию ДО send_message: UNIQUE
            # (user_id, message_id) и (user_id, text_hash) поймают дубль
            # на уровне БД без JOIN-запроса.
            log_ok = await repository.log_notification(
                user_id=user_id,
                message_id=message_db_id,
                text_hash=text_hash_value,
                success=True,
                matched_vacancy_ids=matched_db_ids,
            )
            if not log_ok:
                # Уже уведомили (по message_id ИЛИ по text_hash) — не дублируем.
                continue

            notification_text = self._format_notification(
                post=post, vacancies=vacancies,
                matched_idxs=hit_idxs,
                message=message, chat_username=chat_username,
            )

            kb_buttons: list[list[InlineKeyboardButton]] = []
            for i, db_id in zip(hit_idxs, matched_db_ids):
                title = _vacancy_title(vacancies[i])
                kb_buttons.append([
                    InlineKeyboardButton(
                        text=f"✍ Отклик: {title}"[:64],
                        callback_data=f"respond:{db_id}",
                    )
                ])
            reply_markup = InlineKeyboardMarkup(inline_keyboard=kb_buttons)

            try:
                await self.bot.send_message(
                    user_id,
                    notification_text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=reply_markup,
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("Не удалось отправить пользователю {}: {}", user_id, e)
                await repository.update_notification_failed(
                    user_id=user_id, message_id=message_db_id, error=str(e),
                )
            await asyncio.sleep(0.05)

    async def _process_duplicate(
        self,
        event,  # noqa: ANN001
        canonical_msg,  # noqa: ANN001 — db.models.Message
        text_hash_value: str,
        chat_id: int,
        chat_username: str | None,
    ) -> None:
        """Обработать duplicate-прилёт: записать аудит-row + запустить
        матчинг по уже-извлечённым LLM-вакансиям canonical.

        LLM не дёргаем (главная экономия дедупа). Матчинг нужен — новые
        юзеры, зарегистрированные после canonical-обработки, могут
        матчить тот же кастинг. UNIQUE(user_id, text_hash) в notifications
        не даст уже уведомлённым получить дубль."""
        text = (event.message.message or "").strip()
        dup_id = await repository.insert_duplicate_message(
            tg_chat_id=chat_id,
            tg_chat_username=chat_username,
            tg_message_id=event.message.id,
            text=text,
            text_hash=text_hash_value,
            canonical_message_id=canonical_msg.id,
        )
        logger.info(
            "Дубль: chat={} msg={} text_hash={} canonical={} dup_row={}",
            chat_username or chat_id, event.message.id, text_hash_value,
            canonical_msg.id, dup_id,
        )

        loaded = await repository.get_canonical_with_vacancies(canonical_msg.id)
        if loaded is None:
            logger.warning(
                "Canonical {} не найден при попытке загрузить — skip match",
                canonical_msg.id,
            )
            return
        canon_msg, canon_vacancies = loaded
        post, vac_extractions = matching._orm_to_extractions(canon_msg, canon_vacancies)
        canonical_vacancy_ids = [v.id for v in canon_vacancies]

        # message_db_id для нотификаций — id duplicate-row'а (для аудита
        # «по какому именно прилёту юзеру ушло»). Если dup_id is None
        # (race на (chat_id, msg_id)) — fallback на canonical.id.
        notify_message_id = dup_id if dup_id is not None else canonical_msg.id

        await self._process_canonical(
            message_db_id=notify_message_id,
            text_hash_value=text_hash_value,
            post=post,
            vacancies=vac_extractions,
            vacancy_ids=canonical_vacancy_ids,
            message=event.message,
            chat_username=chat_username,
        )

    async def _handle_message(self, event):
        text = (event.message.message or "").strip()
        if not text:
            return
        logger.debug("Новое сообщение: {!r}", text[:120])

        chat = event.message.chat
        chat_id = getattr(chat, "id", 0)
        chat_username = getattr(chat, "username", None)

        th = text_hash(text)

        # Pre-LLM check: если canonical уже есть в окне 3 дней — duplicate-путь.
        canonical = await repository.find_canonical(th)
        if canonical is not None:
            await self._process_duplicate(event, canonical, th, chat_id, chat_username)
            return

        # LLM extract — race-окно 2-5 секунд.
        post = await self.llm.extract(text)
        logger.info(
            "LLM extract: casting={} project={} city={} vacancies={} conf={:.2f}",
            post.is_casting, post.project_types, post.city,
            len(post.vacancies), post.confidence,
        )

        # Re-check: пока шёл LLM, кто-то другой мог закоммитить canonical
        # с тем же text_hash. Если так — переключаемся в duplicate-путь.
        canonical = await repository.find_canonical(th)
        if canonical is not None:
            logger.info(
                "Race-loser: canonical {} появился во время LLM-extract для hash {}",
                canonical.id, th,
            )
            await self._process_duplicate(event, canonical, th, chat_id, chat_username)
            return

        # Свежий canonical — пишем + матчинг + нотификации.
        message_db_id, vacancy_ids = await repository.insert_message_with_vacancies(
            tg_chat_id=chat_id,
            tg_chat_username=chat_username,
            tg_message_id=event.message.id,
            text=text,
            text_hash=th,
            extracted=post,
        )
        if message_db_id is None:
            logger.warning("insert_message_with_vacancies вернул None — skip")
            return

        await self._process_canonical(
            message_db_id=message_db_id,
            text_hash_value=th,
            post=post,
            vacancies=post.vacancies,
            vacancy_ids=vacancy_ids,
            message=event.message,
            chat_username=chat_username,
        )

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

        logger.info(
            "Userbot запущен, слушаю каналы: {}",
            [getattr(e, "username", getattr(e, "id", "?")) for e in entities],
        )
        await self.client.run_until_disconnected()
