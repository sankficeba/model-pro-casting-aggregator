"""aiogram-бот: приветствие, ссылка на Mini App, админ-команды по каналам."""
from __future__ import annotations

import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardRemove,
)
from loguru import logger
from sqlalchemy import select

from api import profile_repo
from bot.response import compose_response, compose_response_llm
from config import settings
from db import matching, repository
from db.models import Message as MessageRow
from db.session import AsyncSessionLocal
from llm.base import LLMProvider
from userbot.client import Userbot, _vacancy_title

HELP_TEXT_USER = (
    "<b>Команды:</b>\n"
    "/start — приветствие\n"
    "/review — посмотреть накопленные объявления (digest)\n"
    "/help — помощь"
)

HELP_TEXT_ADMIN = HELP_TEXT_USER + (
    "\n\n<b>Админ:</b>\n"
    "/channels — список каналов\n"
    "/addchannel @username — добавить канал\n"
    "/removechannel @username — отключить канал\n"
    "/broadcast_legacy &lt;текст&gt; — разовая рассылка юзерам со старой анкетой"
)

GREETING = (
    "<b>Добро пожаловать в Model Promo Agency!</b> 👋\n\n"
    "Мы рады видеть тебя в нашей команде. Это не просто бот, а мощный "
    "агрегатор вакансий: мы в реальном времени анализируем огромную сеть "
    "каналов и агентств, чтобы ты получал уведомления о кастингах и работе "
    "самым первым! 🚀\n\n"
    "<b>Кого мы ищем?</b>\n"
    "У нас открыт набор на следующие направления:\n\n"
    "🛠 <b>Разнорабочие:</b> хелперы, клининг, грузчики.\n"
    "🎉 <b>Event-персонал:</b> хостес, промо-модели, аниматоры.\n"
    "📸 <b>Творческие позиции:</b> актёры и модели.\n"
    "💻 <b>Администрирование:</b> операторы регистрации, супервайзеры.\n\n"
    "<b>Как начать зарабатывать?</b>\n"
    "Чтобы не пропускать лучшие предложения и настроить уведомления, "
    "открой Mini App рядом с полем ввода и заполни короткую анкету — "
    "там можно выбрать интересующие тебя категории."
)


def _is_admin(user_id: int | None) -> bool:
    return user_id is not None and user_id in settings.admin_ids


def _help_for(user_id: int | None) -> str:
    return HELP_TEXT_ADMIN if _is_admin(user_id) else HELP_TEXT_USER


async def _build_digest_message(
    user_id: int,
    message_id: int,
    matched_vacancy_ids: list[int],
) -> tuple[str, InlineKeyboardMarkup] | None:
    """Загрузить message+vacancies и собрать digest-уведомление с кнопками
    Отклик/Следующее. Возвращает None если canonical исчез."""
    async with AsyncSessionLocal() as session:
        msg_res = await session.execute(
            select(MessageRow).where(MessageRow.id == message_id)
        )
        msg = msg_res.scalar_one_or_none()
        if msg is None:
            return None
        canonical_id = msg.canonical_message_id or msg.id

    loaded = await repository.get_canonical_with_vacancies(canonical_id)
    if loaded is None:
        return None
    canon_msg, canon_vacancies = loaded
    post, vac_extractions = matching._orm_to_extractions(canon_msg, canon_vacancies)

    matched_idxs: list[int] = []
    matched_set = set(matched_vacancy_ids or [])
    for i, v in enumerate(canon_vacancies):
        if v.id in matched_set:
            matched_idxs.append(i)
    if not matched_idxs:
        # Fallback: все вакансии canonical (юзер заматчился раньше, теперь — общая карточка).
        matched_idxs = list(range(len(canon_vacancies)))
    if not matched_idxs:
        return None

    eff_cat = (
        canon_vacancies[matched_idxs[0]].category if canon_vacancies else None
    ) or canon_msg.category

    # У _format_notification ожидает Telethon-like message: .id + .message
    class _PseudoMsg:
        id = canon_msg.tg_message_id
        message = canon_msg.text

    text = Userbot._format_notification(
        post=post,
        vacancies=vac_extractions,
        matched_idxs=matched_idxs,
        message=_PseudoMsg(),
        chat_username=canon_msg.tg_chat_username,
        effective_category=eff_cat,
    )

    pending_left = await repository.count_pending(user_id)
    text += f"\n\n<i>Осталось нерассмотренных: {pending_left}</i>"

    kb_buttons: list[list[InlineKeyboardButton]] = []
    for i in matched_idxs:
        v = canon_vacancies[i]
        title = _vacancy_title(vac_extractions[i])
        kb_buttons.append([
            InlineKeyboardButton(
                text=f"✍ Отклик: {title}"[:64],
                callback_data=f"respond:{v.id}",
            )
        ])
    if pending_left > 0:
        kb_buttons.append([
            InlineKeyboardButton(text="➡ Следующее", callback_data="digest:next")
        ])
    return text, InlineKeyboardMarkup(inline_keyboard=kb_buttons)


async def _send_next_pending(bot: Bot, user_id: int) -> bool:
    """Извлечь следующее pending и отправить юзеру. Возвращает True если
    что-то отправлено, False если очередь пуста (или canonical исчез)."""
    while True:
        item = await repository.pop_next_pending(user_id)
        if item is None:
            return False
        # Записываем в notifications (UNIQUE по user_id+text_hash может
        # отбросить — но тогда мы и не должны слать).
        log_ok = await repository.log_notification(
            user_id=user_id,
            message_id=item["message_id"],
            text_hash=item["text_hash"],
            success=True,
            matched_vacancy_ids=item["matched_vacancy_ids"],
        )
        if not log_ok:
            # Уже было — попробуем следующее
            continue
        built = await _build_digest_message(
            user_id, item["message_id"], item["matched_vacancy_ids"]
        )
        if built is None:
            continue
        text, reply_markup = built
        try:
            await bot.send_message(
                user_id, text,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=reply_markup,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("digest send failed for {}: {}", user_id, e)
            await repository.update_notification_failed(
                user_id=user_id, message_id=item["message_id"], error=str(e),
            )
        return True


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


def build_dispatcher(bot: Bot, llm: LLMProvider | None = None) -> Dispatcher:
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

    @dp.message(Command("review"))
    async def cmd_review(message: Message) -> None:
        """Начать рассматривать накопленные объявления (digest mode)."""
        sent = await _send_next_pending(bot, message.from_user.id)
        if not sent:
            await message.answer("Пока что активных объявлений нет.")

    @dp.callback_query(F.data == "digest:next")
    async def cb_digest_next(query: CallbackQuery) -> None:
        if not query.from_user:
            return
        sent = await _send_next_pending(bot, query.from_user.id)
        if not sent:
            try:
                await query.message.answer("Пока что активных объявлений нет.")  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001
                pass
        await query.answer()

    # ---------- Admin: channels ----------

    @dp.message(Command("channels"))
    async def cmd_channels(message: Message) -> None:
        if not _is_admin(message.from_user.id):
            return
        rows = await repository.list_channels(active_only=False)
        if not rows:
            await message.answer("Список каналов пуст.")
            return
        def _label(r) -> str:
            if r.username:
                return f"@{r.username}"
            if r.tg_chat_id is not None:
                return f"приватный (id {r.tg_chat_id})"
            return f"channel#{r.id}"

        active = [r for r in rows if r.active]
        inactive = [r for r in rows if not r.active]
        lines = ["<b>Активные каналы:</b>"]
        lines += [f"• {_label(r)}" for r in active] or ["—"]
        if inactive:
            lines += ["", "<i>Отключённые:</i>"] + [f"• {_label(r)}" for r in inactive]
        await message.answer("\n".join(lines), parse_mode="HTML")

    @dp.message(Command("addchannel"))
    async def cmd_add_channel(message: Message) -> None:
        if not _is_admin(message.from_user.id):
            return
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await message.answer(
                "Использование:\n"
                "• <code>/addchannel @username</code> — публичный\n"
                "• <code>/addchannel https://t.me/c/&lt;id&gt;</code> — приватный (нужно быть его участником)",
                parse_mode="HTML",
            )
            return
        ch = await repository.add_channel(parts[1], added_by=message.from_user.id)
        if ch is None:
            await message.answer("Канал уже в активном списке или ссылка не распознана.")
            return
        ch_label = (
            f"@{ch.username}" if ch.username else f"приватный (id {ch.tg_chat_id})"
        )
        await _restart_self(bot, message, f"✅ Канал {ch_label} добавлен.")

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

    @dp.message(Command("broadcast_legacy"))
    async def cmd_broadcast_legacy(message: Message) -> None:
        """Разовая рассылка юзерам со старой actor_profile анкетой,
        не успевшим выбрать новую категорию. Текст передаётся в команде.
        """
        if not _is_admin(message.from_user.id):
            return
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await message.answer(
                "Использование: <code>/broadcast_legacy &lt;текст&gt;</code>\n\n"
                "Шлёт указанный текст всем юзерам с заполненным старым "
                "<code>actor_profile</code>, ещё не выбравшим ни одной "
                "новой категории. HTML-разметка поддерживается.",
                parse_mode="HTML",
            )
            return
        body = parts[1]
        user_ids = await repository.list_legacy_unmigrated_users()
        if not user_ids:
            await message.answer("Никого не нашёл (никто не подходит под условие).")
            return
        await message.answer(f"Найдено {len(user_ids)} юзеров. Начинаю рассылку…")
        sent = 0
        failed = 0
        for uid in user_ids:
            try:
                await bot.send_message(uid, body, parse_mode="HTML")
                sent += 1
            except Exception as e:  # noqa: BLE001
                logger.warning("broadcast_legacy: send to {} failed: {}", uid, e)
                failed += 1
            await asyncio.sleep(0.05)
        await message.answer(
            f"Готово. Отправлено: <b>{sent}</b>, ошибок: <b>{failed}</b>.",
            parse_mode="HTML",
        )

    # ---------- Inline-кнопки «Добавить/Не добавлять» под предложением канала ----------

    @dp.callback_query(F.data.startswith("csg:"))
    async def cb_channel_suggestion(query: CallbackQuery) -> None:
        """callback_data: 'csg:add:<ref>' или 'csg:skip:<ref>'.
        Только admin может нажимать."""
        if not _is_admin(query.from_user.id if query.from_user else None):
            await query.answer("Только для админов.", show_alert=True)
            return
        parts = (query.data or "").split(":", 2)
        if len(parts) < 3:
            await query.answer("Битая кнопка.", show_alert=True)
            return
        action, ref = parts[1], parts[2]
        # Восстанавливаем полный ref для repository.add_channel
        full_ref = f"https://t.me/{ref}" if not ref.startswith("c/") else f"https://t.me/{ref}"
        message = query.message  # type: ignore[union-attr]
        if action == "add":
            ch = await repository.add_channel(full_ref, added_by=query.from_user.id)
            if ch is None:
                await query.answer("Канал уже в активном списке или ссылка не распознана.", show_alert=True)
                if message:
                    try:
                        await message.edit_reply_markup(reply_markup=None)
                    except Exception:  # noqa: BLE001
                        pass
                return
            ch_label = (
                f"@{ch.username}" if ch.username else f"приватный (id {ch.tg_chat_id})"
            )
            if message:
                try:
                    await message.edit_text(
                        (message.html_text or "") + f"\n\n✅ <b>Добавлен:</b> {ch_label}",
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
                except Exception:  # noqa: BLE001
                    pass
            await query.answer(f"Добавлено: {ch_label}")
            await _restart_self(bot, message, f"✅ Канал {ch_label} добавлен (через предложение).")  # type: ignore[arg-type]
        elif action == "skip":
            if message:
                try:
                    await message.edit_text(
                        (message.html_text or "") + "\n\n❌ <b>Отклонено</b>",
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
                except Exception:  # noqa: BLE001
                    pass
            await query.answer("Отклонено.")
        else:
            await query.answer("Неизвестное действие.", show_alert=True)

    # ---------- Inline-кнопка «Сгенерировать отклик» под уведомлением ----------

    @dp.callback_query(F.data.startswith("respond:"))
    async def cb_respond(query: CallbackQuery) -> None:
        # callback_data: "respond:<vacancy_id>"
        try:
            vacancy_id = int((query.data or "").split(":", 1)[1])
        except (ValueError, IndexError):
            await query.answer("Некорректные данные кнопки.", show_alert=True)
            return

        user_id = query.from_user.id if query.from_user else 0
        profile = await profile_repo.get_profile(user_id)
        if profile is None:
            await query.answer(
                "Сначала заполни анкету в Mini App — без неё нечего вставлять в отклик.",
                show_alert=True,
            )
            return

        loaded = await repository.get_vacancy_with_message(vacancy_id)
        if loaded is None:
            await query.answer("Вакансия не найдена.", show_alert=True)
            return
        vacancy, message_row = loaded

        # Если LLM-провайдер прокинут — собираем «живой» текст; на любую
        # ошибку (нет сети, плохой JSON и т.п.) compose_response_llm
        # сам откатится на детерминированный шаблон.
        if llm is not None:
            text = await compose_response_llm(profile, message_row, vacancy, llm)
        else:
            text = compose_response(profile, message_row, vacancy)
        # Оборачиваем в <pre> для удобного однотап-копирования в Telegram.
        from html import escape

        body = escape(text)
        try:
            await query.message.answer(  # type: ignore[union-attr]
                f"<b>Готовый отклик</b> — нажми и удерживай, чтобы скопировать:\n\n<pre>{body}</pre>",
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            await query.answer()
        except Exception as e:  # noqa: BLE001
            logger.warning("Не удалось отправить отклик user={}: {}", user_id, e)
            await query.answer("Не получилось отправить отклик. Попробуй ещё раз.", show_alert=True)

    # ---------- Fallback ----------

    @dp.message(F.text)
    async def fallback(message: Message) -> None:
        await message.answer(
            "Не понял. " + _help_for(message.from_user.id),
            parse_mode="HTML",
        )

    return dp


async def run_bot(bot: Bot, llm: LLMProvider | None = None) -> None:
    dp = build_dispatcher(bot, llm=llm)
    logger.info("aiogram-бот запущен")
    await dp.start_polling(bot)
