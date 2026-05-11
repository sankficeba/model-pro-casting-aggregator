"""aiogram-бот: приветствие, ссылка на Mini App, админ-команды по каналам."""
from __future__ import annotations

import asyncio

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
from bot import keyboards
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
    "/channellink &lt;ref&gt; &lt;url&gt; — задать invite-ссылку для приватного канала\n"
    "/broadcast_legacy &lt;текст&gt; — разовая рассылка юзерам со старой анкетой\n"
    "/cancel — отменить ожидаемую рассылку"
)


async def _process_admin_broadcast(
    bot: Bot, message: Message, pending: dict
) -> None:
    """Скопировать сообщение админа всем юзерам, попадающим под фильтр.
    Используется copyMessage (Telegram Bot API) — он сохраняет текст,
    форматирование, медиа, а также премиум-emoji entities."""
    admin_id = message.from_user.id  # type: ignore[union-attr]
    filter_code = pending["filter"]
    await repository.clear_broadcast_pending(admin_id)

    user_ids = await repository.list_broadcast_audience(
        filter_code,
        age_min=pending.get("age_min"),
        age_max=pending.get("age_max"),
        height_min=pending.get("height_min"),
        height_max=pending.get("height_max"),
        name_query=pending.get("name_query"),
    )
    # Не слать админу самому себе.
    user_ids = [uid for uid in user_ids if uid != admin_id]
    if not user_ids:
        await message.answer(
            "В выбранной аудитории сейчас 0 пользователей. Рассылка отменена."
        )
        return

    await message.answer(
        f"⏳ Начинаю рассылку: {len(user_ids)} получателей."
    )
    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await bot.copy_message(
                chat_id=uid,
                from_chat_id=admin_id,
                message_id=message.message_id,
            )
            sent += 1
        except Exception as e:  # noqa: BLE001
            logger.warning("broadcast: copy_message to {} failed: {}", uid, e)
            failed += 1
        await asyncio.sleep(0.04)
    await message.answer(
        f"✅ Готово.\nОтправлено: <b>{sent}</b> · Ошибок: <b>{failed}</b>",
        parse_mode="HTML",
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

    fallback_link = None
    if not canon_msg.tg_chat_username:
        fallback_link, _label = await repository.get_channel_link_for_message(canonical_id)
    text = Userbot._format_notification(
        post=post,
        vacancies=vac_extractions,
        matched_idxs=matched_idxs,
        message=_PseudoMsg(),
        chat_username=canon_msg.tg_chat_username,
        effective_category=eff_cat,
        invite_link=fallback_link,
    )

    pending_left = await repository.count_pending(user_id)
    text += f"\n\n<i>Осталось нерассмотренных: {pending_left}</i>"

    kb_buttons: list[list[InlineKeyboardButton]] = []
    for i in matched_idxs:
        v = canon_vacancies[i]
        title = _vacancy_title(vac_extractions[i])
        kb_buttons.append([
            InlineKeyboardButton(
                text=f"Сгенерировать отклик: {title}"[:64],
                callback_data=f"respond:{v.id}",
                icon_custom_emoji_id=keyboards.EMOJI_RESPOND,
            )
        ])
    fav_state = await repository.is_favorited(user_id, canonical_id)
    kb_buttons += keyboards.actions_rows(message_id=canonical_id, is_favorited=fav_state)
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


async def _channels_changed(
    *,
    bot: Bot,
    message: Message,
    reason: str,
    userbot: Userbot | None,
    action: str,
    ref: str,
) -> None:
    """Hot-reload подписок Telethon после изменения channels. Без
    рестарта процесса (исторически тут был os._exit(0), теряли
    события из всех каналов на ~15 сек)."""
    if userbot is None:
        await message.answer(f"{reason}\n⚠️ userbot не подключён, перезагрузи app вручную.")
        return
    if action == "add":
        ok = await userbot.subscribe_channel(ref)
    elif action == "remove":
        ok = await userbot.unsubscribe_channel(ref)
    else:
        ok = False
    if ok:
        await message.answer(f"{reason}\n✅ Подписки userbot обновлены без рестарта.")
    else:
        await message.answer(
            f"{reason}\n⚠️ Не удалось обновить подписку live (ref={ref}). "
            "Проверь логи app."
        )


def build_dispatcher(
    bot: Bot,
    llm: LLMProvider | None = None,
    userbot: Userbot | None = None,
) -> Dispatcher:
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        await repository.upsert_user(
            message.from_user.id,
            username=message.from_user.username,
        )
        # Активируем пробный период при первом /start.
        active_until = await repository.start_trial_if_first_time(
            message.from_user.id, settings.subscription_trial_days,
        )
        trial_note = ""
        if active_until is not None:
            # Если только что стартовали trial — сообщим об этом.
            status = await repository.get_subscription_status(message.from_user.id)
            if status["is_active"]:
                trial_note = (
                    f"\n\n🎁 <b>Пробный период активирован</b> — "
                    f"бесплатно на {settings.subscription_trial_days} дней "
                    f"(до {active_until.strftime('%d.%m.%Y')})."
                )
        await message.answer(
            GREETING + trial_note + "\n\n" + _help_for(message.from_user.id),
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
        await _channels_changed(
            bot=bot, message=message, userbot=userbot,
            reason=f"✅ Канал {ch_label} добавлен.",
            action="add", ref=parts[1].strip(),
        )

    @dp.message(Command("channellink"))
    async def cmd_set_channel_link(message: Message) -> None:
        """Записать invite-ссылку на приватный канал, чтобы кнопка
        «Подробнее» под уведомлением могла переслать туда юзера.
        Использование:
          /channellink @username https://t.me/+abc123
          /channellink t.me/c/1968214811 https://t.me/+abc123
        Чтобы убрать ссылку — указать слово 'none' вместо URL.
        """
        if not _is_admin(message.from_user.id):
            return
        parts = (message.text or "").split(maxsplit=2)
        if len(parts) < 3 or not parts[1].strip() or not parts[2].strip():
            await message.answer(
                "Использование: <code>/channellink &lt;@username|t.me/c/&lt;id&gt;&gt; "
                "&lt;invite_url&gt;</code>\n"
                "Чтобы очистить — передай <code>none</code> вместо ссылки.",
                parse_mode="HTML",
            )
            return
        ref = parts[1].strip()
        link_arg = parts[2].strip()
        link: str | None = None if link_arg.lower() == "none" else link_arg
        ok = await repository.set_channel_invite_link(ref, link)
        if not ok:
            await message.answer(
                "Канал не найден. Сначала добавь его через <code>/addchannel</code>.",
                parse_mode="HTML",
            )
            return
        if link:
            await message.answer(f"✅ Invite-ссылка сохранена: {link}")
        else:
            await message.answer("✅ Invite-ссылка очищена.")

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
        await _channels_changed(
            bot=bot, message=message, userbot=userbot,
            reason="🗑 Канал отключён.",
            action="remove", ref=parts[1].strip(),
        )

    @dp.message(Command("cancel"))
    async def cmd_cancel(message: Message) -> None:
        if not _is_admin(message.from_user.id):
            await message.answer(
                "Нечего отменять. " + _help_for(message.from_user.id),
                parse_mode="HTML",
            )
            return
        pending = await repository.get_broadcast_pending(message.from_user.id)
        if pending is None:
            await message.answer("Нет ожидающей рассылки.")
            return
        await repository.clear_broadcast_pending(message.from_user.id)
        await message.answer("Рассылка отменена.")

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
            await _channels_changed(
                bot=bot, message=message,  # type: ignore[arg-type]
                userbot=userbot,
                reason=f"✅ Канал {ch_label} добавлен (через предложение).",
                action="add", ref=full_ref,
            )
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

    # ---------- Inline-кнопки под уведомлением: Подробнее / Удалить / Избранное ----------

    @dp.callback_query(F.data.startswith("details:"))
    async def cb_details(query: CallbackQuery) -> None:
        # callback_data: "details:<message_db_id>"
        try:
            msg_id = int((query.data or "").split(":", 1)[1])
        except (ValueError, IndexError):
            await query.answer("Битая кнопка.", show_alert=True)
            return
        link, label = await repository.get_channel_link_for_message(msg_id)
        if link:
            try:
                await query.answer()
                await query.message.answer(  # type: ignore[union-attr]
                    f"🔗 Источник: <b>{label}</b>\n{link}",
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                )
            except Exception:  # noqa: BLE001
                await query.answer(link, show_alert=True)
        else:
            txt = (
                f"У админа пока не указана ссылка на {label or 'этот канал'}. "
                "Попроси добавить её."
            )
            await query.answer(txt, show_alert=True)

    @dp.callback_query(F.data == "delself:")
    async def cb_del_self(query: CallbackQuery) -> None:
        """Удалить из чата само сообщение, на котором висит кнопка."""
        try:
            await query.message.delete()  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            try:
                await query.message.edit_reply_markup(reply_markup=None)  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001
                pass
        await query.answer("Удалено.")

    @dp.callback_query(F.data.startswith("fav:"))
    async def cb_fav(query: CallbackQuery) -> None:
        """callback_data: 'fav:add:<msg_id>' / 'fav:rm:<msg_id>'."""
        parts = (query.data or "").split(":", 2)
        if len(parts) < 3:
            await query.answer("Битая кнопка.", show_alert=True)
            return
        action = parts[1]
        try:
            msg_id = int(parts[2])
        except ValueError:
            await query.answer("Битая кнопка.", show_alert=True)
            return
        user_id = query.from_user.id if query.from_user else 0
        if not user_id:
            await query.answer("Не удалось определить юзера.", show_alert=True)
            return

        if action == "add":
            matched_ids = await repository.get_matched_vacancy_ids(user_id, msg_id)
            await repository.add_favorite(user_id, msg_id, matched_ids)
            new_state = True
            popup = "Добавлено в избранное ⭐"
        elif action == "rm":
            await repository.remove_favorite(user_id, msg_id)
            new_state = False
            popup = "Убрано из избранного"
        else:
            await query.answer("Неизвестное действие.", show_alert=True)
            return

        # Перерисовать клавиатуру: меняем только последний ряд (fav).
        msg = query.message
        if msg is not None and msg.reply_markup is not None:
            try:
                old_rows = list(msg.reply_markup.inline_keyboard)
                # Отбрасываем хвост из 2 рядов (actions) и подставляем новые.
                head = old_rows[:-2]
                new_rows = head + keyboards.actions_rows(
                    message_id=msg_id, is_favorited=new_state,
                )
                await msg.edit_reply_markup(
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=new_rows)
                )
            except Exception:  # noqa: BLE001
                pass
        await query.answer(popup)

    @dp.callback_query(F.data.startswith("problem:resolve:"))
    async def cb_problem_resolve(query: CallbackQuery) -> None:
        """Админ закрывает тикет «Сообщить о проблеме» прямо из чат-нотификации."""
        user_id = query.from_user.id if query.from_user else 0
        if user_id not in settings.admin_ids:
            await query.answer("Только для админов.", show_alert=True)
            return
        parts = (query.data or "").split(":", 2)
        try:
            problem_id = int(parts[2])
        except (ValueError, IndexError):
            await query.answer("Битая кнопка.", show_alert=True)
            return
        changed = await repository.resolve_problem(problem_id)
        msg = query.message
        if msg is not None:
            try:
                old_text = msg.html_text if hasattr(msg, "html_text") else (msg.text or "")
                new_text = f"{old_text}\n\n<i>✅ решено</i>"
                await msg.edit_text(
                    new_text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            except Exception:  # noqa: BLE001
                try:
                    await msg.edit_reply_markup(reply_markup=None)
                except Exception:  # noqa: BLE001
                    pass
        await query.answer("Закрыто." if changed else "Уже было закрыто.")

    # ---------- Admin broadcast OR fallback ----------

    @dp.message()
    async def admin_broadcast_or_fallback(message: Message) -> None:
        """Если у админа есть pending broadcast — рассылаем его сообщение
        (текст/фото/видео/гифку) всем по фильтру. Иначе на текстовое
        сообщение шлём «Не понял», нетекстовые игнорируем."""
        from_user = message.from_user
        if from_user is not None and _is_admin(from_user.id):
            pending = await repository.get_broadcast_pending(from_user.id)
            if pending is not None:
                await _process_admin_broadcast(bot, message, pending)
                return
        if message.text:
            await message.answer(
                "Не понял. " + _help_for(from_user.id if from_user else None),
                parse_mode="HTML",
            )

    return dp


async def run_bot(
    bot: Bot,
    llm: LLMProvider | None = None,
    userbot: Userbot | None = None,
) -> None:
    dp = build_dispatcher(bot, llm=llm, userbot=userbot)
    logger.info("aiogram-бот запущен")
    await dp.start_polling(bot)
