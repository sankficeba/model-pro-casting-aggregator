"""Telethon-userbot: слушает каналы, парсит сообщения через LLM,
пишет историю в БД и рассылает совпадения подходящим анкетам."""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger
from telethon import TelegramClient, events
from telethon.errors import (
    ChannelPrivateError,
    InviteHashExpiredError,
    InviteHashInvalidError,
    UserAlreadyParticipantError,
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import (
    CheckChatInviteRequest,
    ImportChatInviteRequest,
)

from api.reference_data import all_refs
from bot.i18n import Lang, get_lang, t
from config import settings
from db import matching, repository
from db.dedup import text_hash
from llm.base import LLMBillingError, LLMProvider
from models.schemas import PostExtraction, VacancyExtraction

_REFS = all_refs("ru")
_REFS_EN = all_refs("en")
_PROJECT_LABELS = {it["code"]: it["label"] for it in _REFS["project_types"]}
_PROJECT_LABELS_EN = {it["code"]: it["label"] for it in _REFS_EN["project_types"]}
_ROLE_LABELS = {it["code"]: it["label"] for it in _REFS["role_types"]}
_ROLE_LABELS_EN = {it["code"]: it["label"] for it in _REFS_EN["role_types"]}
_WORK_TYPE_LABELS = {
    it["code"]: it["label"]
    for ref_key in ("work_types_event", "work_types_general", "work_types_admin")
    for it in _REFS[ref_key]
}
_WORK_TYPE_LABELS_EN = {
    it["code"]: it["label"]
    for ref_key in ("work_types_event", "work_types_general", "work_types_admin")
    for it in _REFS_EN[ref_key]
}


def _project_labels(lang: Lang) -> dict[str, str]:
    return _PROJECT_LABELS_EN if lang == "en" else _PROJECT_LABELS


def _role_labels(lang: Lang) -> dict[str, str]:
    return _ROLE_LABELS_EN if lang == "en" else _ROLE_LABELS


def _work_type_labels(lang: Lang) -> dict[str, str]:
    return _WORK_TYPE_LABELS_EN if lang == "en" else _WORK_TYPE_LABELS


# Per-category эмодзи (fallback unicode) + название для шапки.
_CATEGORY_HEADERS = {
    "creative": ("🎬", "Творческие позиции"),
    "event":    ("🎉", "Event-персонал"),
    "general":  ("🛠", "Разнорабочие"),
    "admin":    ("🌟", "Администрирование"),
}
_CATEGORY_HEADERS_EN = {
    "creative": ("🎬", "Creative positions"),
    "event":    ("🎉", "Event staff"),
    "general":  ("🛠", "General labor"),
    "admin":    ("🌟", "Administration"),
}

# Premium custom-emoji IDs per category для inline-рендера в HTML тег
# <tg-emoji emoji-id="...">fallback</tg-emoji>. Не-Premium юзеры видят
# fallback unicode внутри тега.
_PREMIUM_CATEGORY_EMOJI_ID = {
    "creative": "5375464961822695044",   # 🎬 кастинг-хлопушка
    "event":    "5461151367559141950",   # 🎉
    "general":  "5393178351844223003",   # 🛠
    "admin":    "5337116611880967451",   # 🌟
}
_PREMIUM_DATE_EMOJI_ID = "5413879192267805083"    # 🗓 календарь


def _premium_emoji(custom_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{custom_id}">{fallback}</tg-emoji>'


# Pull-backup отсекает сообщения старше этого возраста — устаревшие
# вакансии (опубликованы > суток назад) пользователю не нужны.
_PULL_MAX_AGE = timedelta(hours=24)


class _PullEvent:
    """Minimal duck-type для подмены NewMessage-event в pull-backup loop.
    `_handle_message` использует только `.message.message / .message.id /
    .message.chat` — мы их предоставляем явно (chat берётся из entity,
    с которого мы запросили историю, потому что Telethon Message.chat
    может быть None для lazy-resolved сообщений)."""
    def __init__(self, msg, chat_entity):  # noqa: ANN001
        self.message = _PullMessage(msg, chat_entity)


class _PullMessage:
    def __init__(self, msg, chat_entity):  # noqa: ANN001
        self._msg = msg
        self.chat = chat_entity

    @property
    def id(self) -> int:
        return self._msg.id

    @property
    def message(self) -> str:
        return self._msg.message or ""

    @property
    def date(self):  # noqa: ANN201
        return getattr(self._msg, "date", None)


def _labels(codes: list[str], mapping: dict[str, str]) -> str:
    if not codes:
        return "—"
    return ", ".join(mapping.get(c, c) for c in codes)


def _format_age(v: VacancyExtraction, lang: Lang = "ru") -> str:
    if v.age_min is not None and v.age_max is not None:
        return f"{v.age_min}" if v.age_min == v.age_max else f"{v.age_min}–{v.age_max}"
    if v.age_min is not None:
        return t(lang, f"от {v.age_min}", f"from {v.age_min}")
    if v.age_max is not None:
        return t(lang, f"до {v.age_max}", f"up to {v.age_max}")
    return "—"


def _vacancy_title(v: VacancyExtraction, lang: Lang = "ru") -> str:
    """role_label если есть (как извлёк LLM, обычно на русском — исходный
    пост тоже русский) → label из справочника на нужном языке → fallback."""
    if v.role_label:
        return v.role_label
    if v.role_types:
        return _role_labels(lang).get(v.role_types[0], v.role_types[0])
    return t(lang, "Роль", "Role")


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
        # Активные entity-ссылки + текущий NewMessage-handler. Нужны для
        # hot-reload подписок без рестарта процесса (subscribe_channel /
        # unsubscribe_channel дёргают _rebind_handler).
        self._entities: list = []
        self._handler_func = None
        # Дебаунс для алерта "пополните баланс LLM" — при разряженном
        # балансе LLMBillingError сыпется на каждое сообщение (десятки в
        # минуту), а слать админам нужно не чаще раза в час.
        self._last_llm_billing_alert = 0.0

    async def _resolve_one(self, row) -> object | None:  # noqa: ANN001
        """Резолвит ОДИН Channel-row → Telethon entity (best-effort).

        Для public-канала с уже закэшированным `tg_chat_id` сначала пробуем
        резолв по числу — Telethon берёт entity из session-кэша и не дёргает
        `ResolveUsernameRequest`. Это защищает от FloodWait-спирали при
        деплоях, когда контейнер рестартует с холодным кэшем.

        Для свежих public-каналов (tg_chat_id ещё None) — по `@username`,
        и после успешного резолва записываем `entity.id` обратно в БД.
        """
        is_private_only = row.tg_chat_id is not None and row.username is None

        async def _try_get(ref, label: str) -> object | None:
            try:
                return await self.client.get_entity(ref)
            except Exception as e:  # noqa: BLE001
                logger.warning("get_entity({}) не удался: {}", label, e)
                return None

        entity: object | None = None
        invite_link = getattr(row, "invite_link", None)
        ref_for_log = (
            f"id={row.tg_chat_id}" if row.tg_chat_id is not None
            else f"@{row.username}" if row.username
            else f"invite={invite_link}"
        )

        # Путь 1: tg_chat_id известен → идём через session-кэш по числу.
        if row.tg_chat_id is not None:
            entity = await _try_get(row.tg_chat_id, f"id={row.tg_chat_id}")

        # Путь 2: нет id или путь 1 не сработал, но username есть → @username.
        if entity is None and row.username:
            entity = await _try_get(f"@{row.username}", f"@{row.username}")
            if entity is not None and row.tg_chat_id is None:
                # Кэшируем bare entity.id (как делает _handle_message при
                # записи messages.tg_chat_id) чтобы на следующем старте идти
                # Путём 1. Telethon get_entity принимает обе формы и тянет
                # из session-кэша.
                e_id = getattr(entity, "id", None)
                if isinstance(e_id, int):
                    try:
                        await repository.cache_channel_tg_chat_id(row.username, e_id)
                    except Exception as e:  # noqa: BLE001
                        logger.warning(
                            "cache_channel_tg_chat_id({}) не удался: {}",
                            row.username, e,
                        )

        # Путь 3: приватный invite (`https://t.me/+xxx`).
        if entity is None and invite_link and row.tg_chat_id is None:
            entity = await self._resolve_invite(row, invite_link)

        if entity is None:
            logger.error("Не удалось получить entity для {}", ref_for_log)
            return None

        if is_private_only or invite_link:
            logger.info("Слушаю приватный канал {} (entity id={})",
                        ref_for_log, getattr(entity, "id", "?"))
            if not getattr(row, "joined_at", None):
                await repository.mark_channel_joined(row.id)
            return entity

        # Пропускаем JoinChannelRequest если уже подтверждено членство:
        # экономит JoinChannel-бюджет (~30 calls/min) при каждом старте.
        if getattr(row, "joined_at", None):
            return entity

        try:
            await self.client(JoinChannelRequest(entity))
            logger.info("Вступил в канал {} (id={})", ref_for_log, getattr(entity, "id", "?"))
            await repository.mark_channel_joined(row.id)
        except UserAlreadyParticipantError:
            # ВНИМАНИЕ: Telegram отдаёт эту ошибку из stale-кэша даже когда
            # мы РЕАЛЬНО не участники. НЕ маркируем joined_at — иначе уйдём
            # в цикл retry↔verify. verify-loop через iter_dialogs позже
            # подтвердит реальное членство и проставит joined_at сам.
            logger.info(
                "JoinChannelRequest для {} → UserAlreadyParticipantError; "
                "ждём подтверждения через verify-loop",
                ref_for_log,
            )
        except (ChannelPrivateError, InviteHashExpiredError) as e:
            logger.warning("Канал {} недоступен ({}); событий не будет",
                           ref_for_log, type(e).__name__)
            return None
        except Exception as e:  # noqa: BLE001
            # FloodWait и т.п. — не вступили, не добавляем в filter:
            # retry-цикл попробует позже когда окно откроется.
            logger.warning("JoinChannelRequest для {} не прошёл ({}); retry позже",
                           ref_for_log, e)
            return None
        return entity

    async def _resolve_invite(self, row, invite_link: str) -> object | None:
        """Резолвит приватный канал по invite-ссылке `https://t.me/+xxx`.
        Если бот ещё не вступил — Import. Если уже вступил — Check (чтобы
        получить entity без повторного join). После успеха кэшируем
        tg_chat_id, чтобы будущие рестарты резолвили из session-кэша.
        """
        # Извлечь invite hash: всё после '+'.
        h = invite_link.rsplit("/", 1)[-1].lstrip("+")
        if not h:
            logger.warning("Пустой invite hash в '{}'", invite_link)
            return None
        try:
            res = await self.client(ImportChatInviteRequest(h))
            chats = getattr(res, "chats", None) or []
            entity = chats[0] if chats else None
            if entity is not None:
                logger.info("Вступил по invite {} (id={})", invite_link, getattr(entity, "id", "?"))
        except UserAlreadyParticipantError:
            try:
                check = await self.client(CheckChatInviteRequest(h))
                entity = getattr(check, "chat", None)
                logger.info("Уже состою по invite {} (id={})", invite_link, getattr(entity, "id", "?"))
            except Exception as e:  # noqa: BLE001
                logger.warning("CheckChatInvite({}) не удался: {}", invite_link, e)
                return None
        except (InviteHashExpiredError, InviteHashInvalidError) as e:
            logger.warning("Invite {} протух/невалиден ({})", invite_link, type(e).__name__)
            return None
        except Exception as e:  # noqa: BLE001
            logger.warning("ImportChatInvite({}) не удался: {}", invite_link, e)
            return None

        e_id = getattr(entity, "id", None) if entity else None
        if isinstance(e_id, int):
            try:
                await repository.cache_channel_tg_chat_id_by_invite(invite_link, e_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("cache по invite {} не записан: {}", invite_link, exc)
        return entity

    async def _resolve_channels(self) -> list:
        await repository.seed_channels_if_empty(settings.tg_channels, added_by=0)
        rows = await repository.list_channels(active_only=True)
        if not rows:
            logger.warning("Нет активных каналов в БД — userbot работает «вхолостую»")
            return []
        entities: list = []
        for row in rows:
            ent = await self._resolve_one(row)
            if ent is not None:
                entities.append(ent)
        return entities

    async def _rebind_handler(self) -> None:
        """Перевешивает NewMessage-handler с актуальным self._entities.
        Вызывается после live-add/remove канала."""
        if self._handler_func is None:
            return
        try:
            self.client.remove_event_handler(self._handler_func)
        except Exception:  # noqa: BLE001
            pass
        self.client.add_event_handler(
            self._handler_func,
            events.NewMessage(chats=self._entities or None),
        )

    @staticmethod
    def _entity_matches(entity, *, username: str | None, tg_chat_id: int | None) -> bool:
        e_username = (getattr(entity, "username", None) or "").lower()
        e_id = getattr(entity, "id", None)
        if username and e_username == username.lower():
            return True
        if tg_chat_id is not None and e_id is not None:
            # БД хранит -100<id>, Telethon отдаёт bare id. Поддерживаем оба.
            if tg_chat_id == e_id:
                return True
            if abs(tg_chat_id) - 1_000_000_000_000 == e_id:
                return True
        return False

    async def subscribe_channel(self, ref: str) -> bool:
        """Hot-reload: добавить канал в подписку Telethon без рестарта app.
        Канал должен уже быть в `channels` (через repository.add_channel).
        Поддерживает три формы ref: @username, t.me/c/<id>, invite-ссылка.
        Возвращает True, если действительно подписались сейчас."""
        invite_link = repository._parse_invite_ref(ref)
        username: str | None = None
        tg_chat_id: int | None = None
        if invite_link is None:
            username, tg_chat_id = repository._parse_channel_ref(ref)
            if username is None and tg_chat_id is None:
                return False
        # Не дублируем подписку, если уже в self._entities.
        for ent in self._entities:
            if invite_link is None and self._entity_matches(
                ent, username=username, tg_chat_id=tg_chat_id,
            ):
                return False
        rows = await repository.list_channels(active_only=True)
        target = None
        for r in rows:
            if invite_link and getattr(r, "invite_link", None) == invite_link:
                target = r
                break
            if username and r.username == username:
                target = r
                break
            if tg_chat_id is not None and r.tg_chat_id == tg_chat_id:
                target = r
                break
        if target is None:
            return False
        # Если invite-канал уже резолвили (tg_chat_id заполнен), проверим
        # дедуп ещё раз по нему — чтобы не вступать повторно.
        if invite_link and target.tg_chat_id is not None:
            for ent in self._entities:
                if self._entity_matches(
                    ent, username=None, tg_chat_id=target.tg_chat_id,
                ):
                    return False
        entity = await self._resolve_one(target)
        if entity is None:
            return False
        self._entities.append(entity)
        await self._rebind_handler()
        logger.info("Hot-reload: подписался на {}", ref)
        return True

    async def unsubscribe_channel(self, ref: str) -> bool:
        """Hot-reload: убрать канал из подписки Telethon. Никаких сетевых
        вызовов — только локальная фильтрация self._entities + rebind."""
        invite_link = repository._parse_invite_ref(ref)
        if invite_link is not None:
            # Для invite поднимаем tg_chat_id из БД (если уже резолвили) и
            # сравниваем по нему. Если ещё не резолвился — нечего отписывать.
            rows = await repository.list_channels(active_only=False)
            target_id = next(
                (r.tg_chat_id for r in rows
                 if getattr(r, "invite_link", None) == invite_link),
                None,
            )
            if target_id is None:
                return False
            username, tg_chat_id = None, target_id
        else:
            username, tg_chat_id = repository._parse_channel_ref(ref)
            if username is None and tg_chat_id is None:
                return False
        before = len(self._entities)
        self._entities = [
            e for e in self._entities
            if not self._entity_matches(e, username=username, tg_chat_id=tg_chat_id)
        ]
        if len(self._entities) == before:
            return False
        await self._rebind_handler()
        logger.info("Hot-reload: отписался от {}", ref)
        return True

    @staticmethod
    def _format_notification(
        *,
        post: PostExtraction,
        vacancies: list[VacancyExtraction],
        matched_idxs: list[int],
        message,
        chat_username: str | None,
        effective_category: str | None = None,
        invite_link: str | None = None,
        lang: Lang = "ru",
    ) -> str:
        """Карточка для пользователя. Перечисляет только подошедшие вакансии.

        `invite_link` — fallback URL для приватных каналов: если у канала нет
        username (приватка), но есть admin-выставленная invite-ссылка, ставим
        её в «Открыть сообщение» — лучше чем ничего.

        Заголовки/лейблы переводятся через `lang`. Свободный текст поста
        (`post.summary`, `vacancy.description`, `role_label`, `post.city`) —
        как извлёк LLM из исходного канала, канал русскоязычный, поэтому эти
        поля остаются на русском независимо от `lang`.
        """
        link = ""
        if chat_username:
            link = f"https://t.me/{chat_username}/{message.id}"
        elif invite_link:
            link = invite_link

        eff_cat = effective_category or post.category or "creative"
        headers = _CATEGORY_HEADERS_EN if lang == "en" else _CATEGORY_HEADERS
        emoji, cat_label = headers.get(eff_cat, headers["creative"])
        # Premium-эмодзи в шапке — per-category. Если для категории нет
        # premium-id, fallback к обычному unicode.
        header_premium_id = _PREMIUM_CATEGORY_EMOJI_ID.get(eff_cat)
        header_emoji_html = (
            _premium_emoji(header_premium_id, emoji) if header_premium_id else emoji
        )

        # Для creative показываем project_types; для остальных — work_types
        # из подошедших вакансий (всё равно они одной категории).
        if eff_cat == "creative":
            meta_left = t(lang, "Тип проекта: ", "Project type: ") + _labels(
                list(post.project_types), _project_labels(lang),
            )
        else:
            shown_work_types: list[str] = []
            seen: set[str] = set()
            for idx in matched_idxs:
                for code in vacancies[idx].work_types or []:
                    if code not in seen:
                        seen.add(code)
                        shown_work_types.append(code)
            meta_left = t(lang, "Должности: ", "Positions: ") + _labels(
                shown_work_types, _work_type_labels(lang),
            )

        # Дата съёмки/смены — собираем из shooting_date матчнутых вакансий.
        shooting_dates: list[str] = []
        seen_dates: set[str] = set()
        for idx in matched_idxs:
            sd = (vacancies[idx].shooting_date or "").strip()
            if sd and sd not in seen_dates:
                seen_dates.add(sd)
                shooting_dates.append(sd)
        # Если в строке есть «:» или диапазон часов, показываем как
        # «Дата и время», иначе просто «Дата».
        joined_date = ", ".join(shooting_dates)
        has_time = any(
            (":" in d) or ("ч" in d.lower())
            or any(ch.isdigit() and "-" in d for ch in d)
            and not any(month in d.lower() for month in (
                "янв","фев","мар","апр","мая","июн","июл","авг","сен","окт","ноя","дек",
            ))
            for d in shooting_dates
        )
        # Упрощённая эвристика — если строка содержит «:» или «утром/днём/
        # вечером/ночью» считаем что есть время.
        time_markers = (":", "утром", "днём", "днем", "вечером", "ночью", "ночная", "утра", "дня", "вечера")
        has_time = any(any(m in d.lower() for m in time_markers) for d in shooting_dates)
        label = t(lang, "Дата и время", "Date and time") if has_time else t(lang, "Дата", "Date")
        date_line = (
            f"{_premium_emoji(_PREMIUM_DATE_EMOJI_ID, '🗓')} "
            f"<b>{label}:</b> {joined_date}"
            if shooting_dates else None
        )

        lines: list[str] = [
            f"<b>{header_emoji_html} " + t(lang, "Подходящая вакансия — ", "Matching posting — ") + f"{cat_label}</b>",
        ]
        if date_line:
            lines.append("")
            lines.append(date_line)
        lines.append("")
        city_label = t(lang, "Город", "City")
        lines.append(f"{meta_left} | {city_label}: {post.city or '—'}")
        lines.append("<b>" + t(lang, f"Подходящие роли ({len(matched_idxs)}):", f"Matching roles ({len(matched_idxs)}):") + "</b>")
        for idx in matched_idxs:
            v = vacancies[idx]
            gender_label = {"male": t(lang, "м", "m"), "female": t(lang, "ж", "f")}.get(v.gender or "", "—")
            rate_str = f"{v.rate} ₽" if v.rate is not None else t(lang, "ставка не указана", "rate not specified")
            extras: list[str] = []
            if v.height_min is not None or v.height_max is not None:
                lo = v.height_min if v.height_min is not None else ""
                hi = v.height_max if v.height_max is not None else ""
                height_word = t(lang, "рост", "height")
                if lo and hi and lo != hi:
                    extras.append(f"{height_word} {lo}–{hi} см" if lang == "ru" else f"{height_word} {lo}–{hi} cm")
                elif lo and hi and lo == hi:
                    extras.append(f"{height_word} {lo} см" if lang == "ru" else f"{height_word} {lo} cm")
                elif lo:
                    extras.append(t(lang, f"рост от {lo} см", f"height from {lo} cm"))
                elif hi:
                    extras.append(t(lang, f"рост до {hi} см", f"height up to {hi} cm"))
            if v.ethnicity:
                extras.append(", ".join(v.ethnicity))
            extras_str = (" · " + " · ".join(extras)) if extras else ""
            lines.append(
                f"• <b>{_vacancy_title(v, lang)}</b> — {_format_age(v, lang)}, {gender_label}, {rate_str}{extras_str}"
            )

        # Body: предпочитаем описания матчнутых вакансий — они конкретны
        # для роли. post.summary показываем только когда пост одно-ролевой
        # (иначе summary часто описывает другую часть поста, не
        # матчнутую — путаница как с «8 ролей: показано про остеоартрит,
        # а юзер матчанулся на «Зрители с бессонницей»).
        per_role_desc = [
            vacancies[i].description for i in matched_idxs
            if vacancies[i].description
        ]
        if per_role_desc:
            body = "\n\n".join(per_role_desc)
        elif len(vacancies) <= 1:
            body = post.summary or (message.message or "")[:300]
        else:
            body = None
        if body:
            lines.append("")
            lines.append(body)
        if link:
            lines.append(f"\n<a href=\"{link}\">" + t(lang, "Открыть сообщение", "Open post") + "</a>")
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

        # Глобальный blacklist: военная тематика и т.п. отсекается до
        # матчинга. Сообщение остаётся в БД для аудита, но никому не идёт.
        raw_text_for_blocklist = (getattr(message, "message", "") or "").strip()
        if repository.text_has_global_blacklist(raw_text_for_blocklist):
            logger.info(
                "Global blacklist отсёк msg {} (содержит запрещённую подстроку)",
                message_db_id,
            )
            return

        user_to_idxs = await matching.find_matching_vacancies(post, vacancies)
        if not user_to_idxs:
            logger.debug("Нет подходящих анкет для сообщения {}", message_db_id)
            return

        # Применяем per-user blacklist по raw тексту поста: если у юзера
        # есть запрещённые слова и они встречаются в посте — пропускаем.
        raw_text = getattr(message, "message", "") or ""
        allowed_users = set(
            await repository.filter_users_by_blacklist(list(user_to_idxs.keys()), raw_text)
        )
        blocked_count = len(user_to_idxs) - len(allowed_users)
        if blocked_count:
            logger.info(
                "Blacklist отсёк {} юзеров для msg {}", blocked_count, message_db_id,
            )
        user_to_idxs = {uid: idxs for uid, idxs in user_to_idxs.items() if uid in allowed_users}
        if not user_to_idxs:
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

            # Подписка: если истекла, переключаемся в degraded mode «1 в день».
            # Если уже отправляли в последние 24ч — пропускаем.
            if not await repository.is_subscription_active(user_id):
                if await repository.should_throttle_after_expiry(user_id):
                    continue
                # send-after-expiry разрешён, но всё равно проходит через
                # обычный путь ниже; запишем timestamp, если send удастся.
                await repository.record_after_expiry_send(user_id)

            # Если у юзера digest или сейчас ночное окно — кладём в очередь
            # вместо немедленной отправки. Дедуп через UNIQUE(user_id, text_hash)
            # как у обычных нотификаций.
            if await repository.should_queue_for_user(user_id):
                queued = await repository.enqueue_pending_notification(
                    user_id=user_id,
                    message_id=message_db_id,
                    text_hash=text_hash_value,
                    matched_vacancy_ids=matched_db_ids,
                )
                if queued:
                    logger.info(
                        "Queued for digest user={} msg={}", user_id, message_db_id,
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

            # Все hit_idxs одного юзера — из одной категории (загружаются
            # одна *Profile-таблица в matching), берём категорию первой
            # подошедшей вакансии.
            first_matched = vacancies[hit_idxs[0]]
            eff_cat = first_matched.category or post.category
            fallback_link = None
            if not chat_username:
                fallback_link = await repository.get_message_permalink(message_db_id)
            # Live push — нет живого Update с language_code, только явный
            # оверрайд из /language (или ru по умолчанию).
            user_lang = await get_lang(user_id, None)
            notification_text = self._format_notification(
                post=post, vacancies=vacancies,
                matched_idxs=hit_idxs,
                message=message, chat_username=chat_username,
                effective_category=eff_cat,
                invite_link=fallback_link,
                lang=user_lang,
            )

            from bot.keyboards import EMOJI_RESPOND, actions_rows
            kb_buttons: list[list[InlineKeyboardButton]] = []
            for i, db_id in zip(hit_idxs, matched_db_ids):
                title = _vacancy_title(vacancies[i], user_lang)
                kb_buttons.append([
                    InlineKeyboardButton(
                        text=t(user_lang, f"Сгенерировать отклик: {title}", f"Generate response: {title}")[:64],
                        callback_data=f"respond:{db_id}",
                        icon_custom_emoji_id=EMOJI_RESPOND,
                    )
                ])
            kb_buttons += actions_rows(message_id=message_db_id, is_favorited=False, lang=user_lang)
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
                if repository.is_bot_chat_dead_error(str(e)):
                    try:
                        await repository.mark_user_bot_chat_inactive(user_id)
                    except Exception:  # noqa: BLE001
                        pass
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

    async def _alert_admins_llm_billing(self) -> None:
        """Шлёт админам «пополните баланс LLM», но не чаще раза в час —
        при разряженном балансе LLMBillingError сыпется на каждое
        сообщение, и без дебаунса это был бы спам."""
        now = time.monotonic()
        if now - self._last_llm_billing_alert < 3600:
            return
        self._last_llm_billing_alert = now
        for admin_id in settings.admin_ids:
            try:
                await self.bot.send_message(
                    admin_id,
                    "⚠️ Баланс LLM (OpenAI) исчерпан — обработка кастингов остановлена. "
                    "Пополните баланс, накопленные сообщения переобработаются автоматически.",
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("LLM billing alert failed for admin {}: {}", admin_id, e)

    async def _handle_message(self, event, origin: str = "push"):
        text = (event.message.message or "").strip()
        if not text:
            return

        chat = event.message.chat
        chat_id = getattr(chat, "id", 0)
        chat_username = getattr(chat, "username", None)
        msg_id = getattr(event.message, "id", 0)
        # Возраст сообщения: для отладки лага push vs pull. Если у Telethon
        # Message есть .date — считаем дельту от now (UTC).
        msg_date = getattr(event.message, "date", None)
        age_sec: float | None = None
        if msg_date is not None:
            try:
                age_sec = (datetime.now(timezone.utc) - msg_date).total_seconds()
            except Exception:  # noqa: BLE001
                age_sec = None
        logger.info(
            "msg origin={} chat={} tg_msg_id={} age={}s text={!r}",
            origin,
            chat_username or chat_id,
            msg_id,
            f"{age_sec:.1f}" if age_sec is not None else "?",
            text[:80],
        )

        th = text_hash(text)

        # Pre-LLM check: если canonical уже есть в окне 3 дней — duplicate-путь.
        canonical = await repository.find_canonical(th)
        if canonical is not None:
            await self._process_duplicate(event, canonical, th, chat_id, chat_username)
            return

        # LLM extract — race-окно 2-5 секунд.
        try:
            post = await self.llm.extract(text)
        except LLMBillingError:
            logger.warning(
                "LLM billing error — сохраняем msg_id={} для retry", event.message.id
            )
            await self._alert_admins_llm_billing()
            message_db_id, _ = await repository.insert_message_with_vacancies(
                tg_chat_id=chat_id,
                tg_chat_username=chat_username,
                tg_message_id=event.message.id,
                text=text,
                text_hash=th,
                extracted=PostExtraction(confidence=0.0),
            )
            if message_db_id is not None:
                await repository.mark_for_llm_retry(message_db_id)
            return
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

    async def _llm_retry_loop(self) -> None:
        """Каждые 5 минут повторно прогоняет через LLM сообщения,
        сохранённые с llm_retry_needed=True из-за нехватки баланса."""
        import types as _types
        while True:
            try:
                await asyncio.sleep(300)
                pending = await repository.get_messages_for_llm_retry()
                if not pending:
                    continue
                logger.info("LLM retry: {} сообщений в очереди", len(pending))
                for msg_id, text, text_hash_val, chat_username, tg_message_id in pending:
                    try:
                        post = await self.llm.extract(text)
                    except LLMBillingError:
                        logger.debug("LLM retry: баланс ещё не пополнен, прерываем")
                        await self._alert_admins_llm_billing()
                        break
                    vacancy_ids = await repository.apply_llm_retry(msg_id, post)
                    if post.is_casting and vacancy_ids:
                        fake_msg = _types.SimpleNamespace(message=text, id=tg_message_id)
                        await self._process_canonical(
                            message_db_id=msg_id,
                            text_hash_value=text_hash_val,
                            post=post,
                            vacancies=post.vacancies,
                            vacancy_ids=vacancy_ids,
                            message=fake_msg,
                            chat_username=chat_username,
                        )
                    await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                logger.exception("llm_retry_loop error: {}", e)

    async def _pull_backup_loop(self, idle_sec: int = 2) -> None:
        """Подстраховка против задержки Telegram event-delivery:
        непрерывно опрашивает GetHistory по каждому слушаемому каналу.
        После полного прохода — небольшой idle (`idle_sec`), затем сразу
        новый проход. Это гарантирует доставку <1 мин даже когда
        NewMessage-push задерживается на стороне Telegram.

        Если Telegram уже доставил NewMessage — наша запись в `messages`
        UNIQUE по (tg_chat_id, tg_message_id) поймает дубль, плюс
        canonical-lookup по text_hash в `_handle_message` дополнительно
        отсечёт повторный LLM-вызов. Pull-backup не дублирует уведомления.

        Throttle между каналами 0.1 сек = 10 RPC/сек, в 3 раза ниже
        безопасного лимита GetHistory (~30/сек).
        """
        # Прогрев last_seen из БД, чтобы при свежем старте не залить пайплайн
        # тоннами «новых» сообщений 3-дневной давности (canonical lookup всё
        # равно их отсеет, но это лишний LLM-расход).
        self._last_seen_msg_id = await repository.get_last_seen_msg_per_channel()
        logger.info(
            "pull-backup: загружено {} last_seen меток",
            len(self._last_seen_msg_id),
        )
        # Первая итерация через 60 сек после старта — дать _resolve_channels
        # отработать.
        await asyncio.sleep(60)
        while True:
            try:
                now = datetime.now(timezone.utc)
                for entity in list(self._entities):
                    bare = abs(getattr(entity, "id", 0))
                    if bare > 1_000_000_000_000:
                        bare -= 1_000_000_000_000
                    if bare == 0:
                        continue
                    last = self._last_seen_msg_id.get(bare, 0)
                    try:
                        msgs = []
                        # iter_messages выдаёт новейшие первыми; ограничим
                        # окно — обычно 1-2 новых за интервал.
                        async for m in self.client.iter_messages(entity, limit=10, min_id=last):
                            if m and m.id > last:
                                msgs.append(m)
                        if msgs:
                            handled = 0
                            skipped_old = 0
                            # Перевернём в хронологический порядок.
                            for m in reversed(msgs):
                                # Bump last_seen всегда — иначе будем повторно
                                # тянуть старые сообщения каждый цикл.
                                self._last_seen_msg_id[bare] = max(
                                    self._last_seen_msg_id.get(bare, 0), m.id,
                                )
                                # Отсечка по возрасту: вакансии старше 24ч
                                # никого уже не интересуют. pull-backup
                                # имеет смысл только как страховка от
                                # задержек event-доставки.
                                msg_date = getattr(m, "date", None)
                                if msg_date is not None:
                                    age = now - msg_date
                                    if age > _PULL_MAX_AGE:
                                        skipped_old += 1
                                        continue
                                await self._handle_message(_PullEvent(m, entity), origin="pull")
                                handled += 1
                            if handled or skipped_old:
                                logger.info(
                                    "pull-backup: chat={} обработано={} пропущено_старых={} "
                                    "(last={})",
                                    bare, handled, skipped_old,
                                    self._last_seen_msg_id[bare],
                                )
                    except Exception as e:  # noqa: BLE001
                        logger.warning("pull-backup({}) не удался: {}", bare, e)
                    # Throttle: 10 RPC/сек — далеко от лимита (~30/сек).
                    await asyncio.sleep(0.1)
            except Exception as e:  # noqa: BLE001
                logger.exception("pull-backup loop error: {}", e)
            # Continuous polling: только короткая пауза между full-pass'ами.
            await asyncio.sleep(idle_sec)

    async def _verify_membership_loop(self, interval_sec: int = 3600) -> None:
        """Раз в N секунд снимает фактический список dialogs аккаунта и
        делает bidirectional sync с `channels.joined_at`:
        - есть в dialogs, joined_at NULL → SET (подтверждаем членство).
        - помечен joined, но НЕ в dialogs → сбрасываем joined_at
          (Telegram отдавал ложный UserAlreadyParticipant из кэша).
        Эта пара правил блокирует цикл «retry-set / verify-clear».
        """
        # Первый прогон через минуту после старта — дать main userbot'у
        # «отдышаться» после _resolve_channels.
        await asyncio.sleep(60)
        while True:
            try:
                real_ids: set[int] = set()
                # archived=None — захватываем все папки/архивы (мы реально
                # участник даже если канал в архиве).
                async for d in self.client.iter_dialogs(archived=None):
                    if d.is_channel or d.is_group:
                        real_ids.add(d.entity.id)
                rows = await repository.list_channels(active_only=True)
                stale: list[int] = []
                confirm: list[int] = []
                for r in rows:
                    if r.tg_chat_id is None:
                        continue
                    bare = abs(r.tg_chat_id)
                    if bare > 1_000_000_000_000:
                        bare -= 1_000_000_000_000
                    really_in = bare in real_ids
                    if really_in and r.joined_at is None:
                        confirm.append(r.id)
                    elif not really_in and r.joined_at is not None:
                        stale.append(r.id)
                if confirm:
                    for cid in confirm:
                        await repository.mark_channel_joined(cid)
                    logger.info(
                        "verify-membership: подтверждено членство для {} каналов",
                        len(confirm),
                    )
                if stale:
                    cleared = await repository.bulk_clear_joined_at(stale)
                    logger.warning(
                        "verify-membership: {} каналов помечены joined но нас нет в dialogs — "
                        "сброшено для retry", cleared,
                    )
                if not stale and not confirm:
                    logger.info(
                        "verify-membership: всё в синке ({} помеченных)",
                        sum(1 for r in rows if r.joined_at is not None),
                    )
            except Exception as e:  # noqa: BLE001
                logger.exception("verify-membership loop error: {}", e)
            await asyncio.sleep(interval_sec)

    async def _retry_pending_joins_loop(self, interval_sec: int = 300) -> None:
        """Периодически пробует вступить в active-каналы с joined_at IS NULL.
        Throttle: не больше 5 JoinChannelRequest в минуту (12с между
        попытками) — чтобы Telegram не растил FloodWait-окно."""
        while True:
            await asyncio.sleep(interval_sec)
            try:
                pending = await repository.list_pending_join_channels()
                if not pending:
                    continue
                logger.info("retry-join: {} каналов в очереди", len(pending))
                added = 0
                for row in pending:
                    await asyncio.sleep(12.0)
                    ent = await self._resolve_one(row)
                    if ent is None:
                        continue
                    # Дедуп защита.
                    dup = False
                    for e in self._entities:
                        if self._entity_matches(
                            e, username=row.username, tg_chat_id=row.tg_chat_id,
                        ):
                            dup = True
                            break
                    if dup:
                        continue
                    self._entities.append(ent)
                    added += 1
                if added > 0:
                    await self._rebind_handler()
                    logger.info("retry-join: подписался на {} новых каналов", added)
            except Exception as e:  # noqa: BLE001
                logger.exception("retry-join loop error: {}", e)

    async def send_original_media(
        self,
        bot: "Bot",
        user_id: int,
        tg_chat_id: int | None,
        tg_chat_username: str | None,
        tg_message_id: int,
        reply_to_msg_id: int,
        caption_html: str | None = None,
        reply_markup=None,
    ) -> bool:
        """Скачать медиафайлы оригинального поста и отправить через бота.

        caption_html — текст для подписи к медиа (HTML, макс. 1024 символа).
        Возвращает True если хотя бы один файл был отправлен.
        """
        from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto
        from aiogram.types import (
            BufferedInputFile,
            InputMediaDocument,
            InputMediaPhoto,
            InputMediaVideo,
            ReplyParameters,
        )

        entity = tg_chat_username or tg_chat_id
        if not entity:
            return False

        try:
            target = await self.client.get_messages(entity, ids=tg_message_id)
            if not target or not target.media:
                return False

            # Собираем все сообщения альбома (grouped_id), иначе — одно
            to_send = [target]
            grouped_id = getattr(target, "grouped_id", None)
            if grouped_id:
                sibling_ids = list(range(max(1, tg_message_id - 9), tg_message_id + 10))
                siblings = await self.client.get_messages(entity, ids=sibling_ids)
                to_send = [
                    m for m in (siblings if isinstance(siblings, list) else [siblings])
                    if m and getattr(m, "grouped_id", None) == grouped_id
                ]

            MAX_BYTES = 50 * 1024 * 1024
            CAPTION_LIMIT = 1024
            reply_params = ReplyParameters(message_id=reply_to_msg_id)
            cap = caption_html[:CAPTION_LIMIT] if caption_html else None

            # Скачиваем все файлы
            items: list[tuple[bytes, str, str]] = []  # (data, media_type, fname)
            for m in to_send:
                if not m or not m.media:
                    continue
                if hasattr(m, "file") and m.file and m.file.size and m.file.size > MAX_BYTES:
                    logger.info("Медиа слишком большое ({:.1f} MB), пропускаем",
                                m.file.size / 1024 / 1024)
                    continue
                try:
                    data = await self.client.download_media(m, bytes)
                    if not data:
                        continue
                    fname = (m.file.name if m.file and m.file.name else "media")
                    if isinstance(m.media, MessageMediaPhoto):
                        items.append((data, "photo", fname or "photo.jpg"))
                    elif isinstance(m.media, MessageMediaDocument):
                        mime = getattr(m.document, "mime_type", "") or ""
                        mtype = "video" if mime.startswith("video/") else "document"
                        items.append((data, mtype, fname or "file"))
                except Exception as e:  # noqa: BLE001
                    logger.warning("Ошибка скачивания медиаitem: {}", e)

            if not items:
                return False

            if len(items) == 1:
                data, mtype, fname = items[0]
                buf = BufferedInputFile(data, filename=fname)
                kw = dict(reply_parameters=reply_params, caption=cap,
                          parse_mode="HTML" if cap else None,
                          reply_markup=reply_markup)
                if mtype == "photo":
                    await bot.send_photo(user_id, buf, **kw)
                elif mtype == "video":
                    await bot.send_video(user_id, buf, **kw)
                else:
                    await bot.send_document(user_id, buf, **kw)
            else:
                # Альбом — caption на первый элемент, reply_markup недоступен
                tg_media = []
                for i, (data, mtype, fname) in enumerate(items):
                    buf = BufferedInputFile(data, filename=fname)
                    item_cap = cap if i == 0 else None
                    item_pm = "HTML" if (i == 0 and cap) else None
                    if mtype == "photo":
                        tg_media.append(InputMediaPhoto(media=buf, caption=item_cap, parse_mode=item_pm))
                    elif mtype == "video":
                        tg_media.append(InputMediaVideo(media=buf, caption=item_cap, parse_mode=item_pm))
                    else:
                        tg_media.append(InputMediaDocument(media=buf, caption=item_cap, parse_mode=item_pm))
                await bot.send_media_group(user_id, media=tg_media, reply_parameters=reply_params)

            return True

        except Exception as e:  # noqa: BLE001
            logger.warning("send_original_media error user={}: {}", user_id, e)
            return False

        except Exception as e:  # noqa: BLE001
            logger.warning("send_original_media error user={}: {}", user_id, e)

    async def start(self) -> None:
        # Ретраим временные сетевые сбои (DNS/маршрутизация до Telegram)
        # здесь, а не даём им всплыть в asyncio.gather в main() — иначе
        # падает весь процесс (и aiogram-бот тоже), Docker его перезапускает,
        # и это выглядит как бесконечный "деплой" каждые ~30 секунд.
        delay = 5.0
        while True:
            try:
                await self.client.start(phone=settings.tg_phone)
                break
            except (ConnectionError, OSError) as e:
                logger.warning(
                    "Userbot: не удалось подключиться к Telegram ({}), повтор через {:.0f}s",
                    e, delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, 120.0)
        self._entities = await self._resolve_channels()
        if not self._entities:
            logger.warning(
                "Список каналов пуст или ни один не разрешился — userbot работает «вхолостую»"
            )

        async def _handler(event):  # noqa: ANN001
            await self._handle_message(event)

        # Сохраняем функцию для последующих rebind'ов в hot-reload.
        self._handler_func = _handler
        self.client.add_event_handler(
            _handler,
            events.NewMessage(chats=self._entities or None),
        )

        logger.info(
            "Userbot запущен, слушаю каналы: {}",
            [getattr(e, "username", getattr(e, "id", "?")) for e in self._entities],
        )
        # Фоновая задача: добиваем зафейленные join'ы по мере восстановления флуда.
        asyncio.create_task(self._retry_pending_joins_loop())
        # Фоновая верификация: раз в час сверяем joined_at с реальными dialogs.
        asyncio.create_task(self._verify_membership_loop())
        # Pull-backup: подстраховка от задержек Telegram event-delivery.
        asyncio.create_task(self._pull_backup_loop())
        await self.client.run_until_disconnected()
