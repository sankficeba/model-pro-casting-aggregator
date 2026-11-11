"""Экраны, перенесённые из Mini App в главное меню бота:
избранное, доставка уведомлений, чёрный список слов, предложить канал,
сообщить о проблеме.

Ввод текста (слова, ссылка на канал, описание проблемы) — через FSM
(MemoryStorage диспетчера). Любая другая кнопка или /start, /menu
сбрасывают ожидание ввода.
"""
from __future__ import annotations

import html
import re
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy import select

from bot import keyboards
from bot.i18n import Lang, t
from bot.menu import CB_MAIN, _btn, _edit_or_send, _lang_of, tge
from config import settings
from db import repository

# Premium emoji (NewsEmoji).
E_FAV = "5222444124698853913"        # 🔖
E_DELIVERY = "5341715473882955310"   # ⚙️
E_BAN = "5240241223632954241"        # 🚫
E_MEGAPHONE = "5424818078833715060"  # 📣
E_WARN = "5447644880824181073"       # ⚠️

CB_FAVS = "favs:list"            # не "fav:" — тот префикс занят кнопками под уведомлениями
CB_DELIVERY = "dlv:menu"
CB_BLACKLIST = "bl:menu"
CB_SUGGEST = "sc:start"
CB_PROBLEM = "pr:start"

# Кнопки, которые сами переводят в режим ввода — middleware их не сбрасывает.
INPUT_STARTERS = {"bl:add", CB_SUGGEST, CB_PROBLEM}

RETENTION_OPTIONS = [1, 3, 5, 7, 14, 30, 0]
FAVS_SHOWN = 20
BLACKLIST_MAX = 200
BL_BUTTONS_SHOWN = 30


class Input(StatesGroup):
    blacklist_add = State()
    suggest_channel = State()
    report_problem = State()


def main_menu_rows(lang: Lang) -> list[list[InlineKeyboardButton]]:
    """Ряды кнопок для главного меню."""
    return [
        [
            _btn(t(lang, "Избранное", "Favorites"), E_FAV, callback_data=CB_FAVS),
            _btn(t(lang, "Доставка", "Delivery"), E_DELIVERY, callback_data=CB_DELIVERY),
        ],
        [
            _btn(t(lang, "Чёрный список", "Blocked words"), E_BAN, callback_data=CB_BLACKLIST),
            _btn(t(lang, "Предложить канал", "Suggest channel"), E_MEGAPHONE, callback_data=CB_SUGGEST),
        ],
        [_btn(t(lang, "Сообщить о проблеме", "Report a problem"), E_WARN, callback_data=CB_PROBLEM)],
    ]


def _back_row(lang: Lang, cb: str = CB_MAIN) -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=t(lang, "⬅️ Назад", "⬅️ Back"), callback_data=cb)]


def _kb(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


class ClearInputOnCallback(BaseMiddleware):
    """Нажатие любой inline-кнопки (кроме тех, что начинают ввод) отменяет
    ожидание текста — иначе следующее сообщение ушло бы не туда."""

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        state: FSMContext | None = data.get("state")
        if state is not None and (event.data or "") not in INPUT_STARTERS:
            if await state.get_state() is not None:
                await state.clear()
        return await handler(event, data)


# ---------------------------------------------------------------- Избранное

def _retention_label(days: int, lang: Lang) -> str:
    if days <= 0:
        return t(lang, "не удалять", "never")
    return t(lang, f"через {days} дн.", f"after {days} d")


async def _fav_titles(message_ids: list[int]) -> dict[int, str]:
    """Короткие названия для кнопок: роль первой вакансии или первая строка текста."""
    from db.models import Message as MessageRow, Vacancy
    from db.session import AsyncSessionLocal

    if not message_ids:
        return {}
    async with AsyncSessionLocal() as s:
        texts = dict((await s.execute(
            select(MessageRow.id, MessageRow.text).where(MessageRow.id.in_(message_ids))
        )).all())
        roles: dict[int, str] = {}
        for mid, role in (await s.execute(
            select(Vacancy.message_id, Vacancy.role_label)
            .where(Vacancy.message_id.in_(message_ids))
            .order_by(Vacancy.message_id, Vacancy.idx)
        )).all():
            if role and mid not in roles:
                roles[mid] = role
    out: dict[int, str] = {}
    for mid in message_ids:
        title = roles.get(mid)
        if not title:
            lines = [ln.strip() for ln in (texts.get(mid) or "").splitlines() if ln.strip()]
            title = lines[0] if lines else "—"
        out[mid] = title
    return out


async def render_favorites(user_id: int, lang: Lang) -> tuple[str, InlineKeyboardMarkup]:
    try:
        await repository.prune_old_favorites(user_id)
    except Exception:  # noqa: BLE001
        pass
    favs = await repository.list_favorites(user_id)
    retention = await repository.get_favorites_retention_days(user_id)
    shown = favs[:FAVS_SHOWN]
    titles = await _fav_titles([f.message_id for f in shown])

    text = tge(E_FAV, "🔖") + t(lang, " <b>Избранные вакансии</b>\n\n", " <b>Favorite postings</b>\n\n")
    if not favs:
        text += t(
            lang,
            "Пока пусто. Добавляй вакансии кнопкой «Добавить в избранное» под уведомлением.",
            "Nothing here yet. Use the \"Add to favorites\" button under a notification.",
        )
    else:
        text += t(
            lang,
            f"Сохранено: <b>{len(favs)}</b>. Нажми на вакансию — бот пришлёт её в чат.",
            f"Saved: <b>{len(favs)}</b>. Tap a posting and the bot will send it to the chat.",
        )
        if len(favs) > FAVS_SHOWN:
            text += t(lang, f"\nПоказаны последние {FAVS_SHOWN}.", f"\nShowing the latest {FAVS_SHOWN}.")
    text += t(lang, "\n\n🗑 Автоудаление: ", "\n\n🗑 Auto-delete: ") + _retention_label(retention, lang)

    rows = [
        [InlineKeyboardButton(
            text=f"{i}. {titles.get(f.message_id, '—')}"[:60],
            callback_data=f"favs:show:{f.message_id}",
        )]
        for i, f in enumerate(shown, 1)
    ]
    rows.append([InlineKeyboardButton(
        text=t(lang, "🗑 Автоудаление: ", "🗑 Auto-delete: ") + _retention_label(retention, lang),
        callback_data="favs:ret",
    )])
    rows.append(_back_row(lang))
    return text, _kb(rows)


async def cb_favs(query: CallbackQuery) -> None:
    lang = await _lang_of(query)
    text, kb = await render_favorites(query.from_user.id, lang)
    await _edit_or_send(query, text, kb)
    await query.answer()


async def cb_favs_retention(query: CallbackQuery) -> None:
    lang = await _lang_of(query)
    cur = await repository.get_favorites_retention_days(query.from_user.id)
    idx = RETENTION_OPTIONS.index(cur) if cur in RETENTION_OPTIONS else -1
    nxt = RETENTION_OPTIONS[(idx + 1) % len(RETENTION_OPTIONS)]
    await repository.set_favorites_retention_days(query.from_user.id, nxt)
    text, kb = await render_favorites(query.from_user.id, lang)
    await _edit_or_send(query, text, kb)
    await query.answer(t(lang, "Сохранено", "Saved"))


async def cb_favs_show(query: CallbackQuery) -> None:
    from api.main import _build_favorite_message  # ленивый импорт: тяжёлый модуль

    lang = await _lang_of(query)
    try:
        message_id = int((query.data or "").rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await query.answer()
        return
    fav = await repository.get_favorite(query.from_user.id, message_id)
    if fav is None:
        await query.answer(t(lang, "Уже не в избранном.", "No longer in favorites."), show_alert=True)
        return
    built = await _build_favorite_message(query.from_user.id, message_id, list(fav.matched_vacancy_ids or []))
    if built is None:
        await query.answer(t(lang, "Это объявление больше недоступно.", "This posting is no longer available."), show_alert=True)
        return
    text, markup = built
    await query.message.answer(  # type: ignore[union-attr]
        text, parse_mode="HTML", disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup.model_validate(markup),
    )
    await query.answer()


# ---------------------------------------------------------------- Доставка

_DELIVERY_KEYS = (
    "delivery_mode", "night_mode_enabled", "night_start_hour",
    "night_end_hour", "digest_daily_enabled", "digest_daily_hour",
)
_HOUR_FIELDS = {"dh": "digest_daily_hour", "ns": "night_start_hour", "ne": "night_end_hour"}


def _on_off(v: bool, lang: Lang) -> str:
    return t(lang, "вкл", "on") if v else t(lang, "выкл", "off")


async def _save_delivery(user_id: int, **changes: Any) -> dict:
    cur = await repository.get_delivery_settings(user_id)
    data = {k: cur[k] for k in _DELIVERY_KEYS}
    data.update(changes)
    return await repository.set_delivery_settings(user_id, **data)


async def render_delivery(user_id: int, lang: Lang) -> tuple[str, InlineKeyboardMarkup]:
    s = await repository.get_delivery_settings(user_id)
    pending = await repository.count_pending(user_id)
    digest = s["delivery_mode"] == "digest"

    text = tge(E_DELIVERY, "⚙️") + t(lang, " <b>Доставка уведомлений</b>\n\n", " <b>Notification delivery</b>\n\n")
    if digest:
        text += t(
            lang,
            "Режим: <b>накопить и просмотреть</b> — объявления копятся, листаешь их в чате кнопкой «следующая вакансия».\n"
            f"📬 Накоплено: <b>{pending}</b>",
            "Mode: <b>collect and review</b> — postings pile up and you flip through them with the \"next posting\" button.\n"
            f"📬 Collected: <b>{pending}</b>",
        )
        if s["digest_daily_enabled"]:
            text += t(lang, f"\n☀️ Сводка каждый день в {s['digest_daily_hour']:02d}:00 МСК",
                      f"\n☀️ Daily digest at {s['digest_daily_hour']:02d}:00 MSK")
    else:
        text += t(lang, "Режим: <b>сразу</b> — уведомление приходит, как только появляется подходящий кастинг.",
                  "Mode: <b>instant</b> — you get a notification as soon as a matching casting appears.")
    if s["night_mode_enabled"]:
        text += t(lang, f"\n🌙 Ночью ({s['night_start_hour']:02d}:00–{s['night_end_hour']:02d}:00 МСК) не беспокоим, утром придёт сводка.",
                  f"\n🌙 Quiet at night ({s['night_start_hour']:02d}:00–{s['night_end_hour']:02d}:00 MSK), morning summary.")

    rows: list[list[InlineKeyboardButton]] = [[
        InlineKeyboardButton(text=("✅ " if not digest else "") + t(lang, "Сразу", "Instant"), callback_data="dlv:mode:instant"),
        InlineKeyboardButton(text=("✅ " if digest else "") + t(lang, "Накопить", "Collect"), callback_data="dlv:mode:digest"),
    ]]
    if digest:
        if pending > 0:
            rows.append([InlineKeyboardButton(
                text=t(lang, f"📬 Посмотреть накопленные ({pending})", f"📬 Review collected ({pending})"),
                callback_data="digest:next",
            )])
            rows.append([InlineKeyboardButton(text=t(lang, "🗑 Очистить накопленные", "🗑 Clear collected"), callback_data="dlv:clear")])
        rows.append([InlineKeyboardButton(
            text=t(lang, "☀️ Сводка каждый день: ", "☀️ Daily digest: ") + _on_off(s["digest_daily_enabled"], lang),
            callback_data="dlv:daily",
        )])
        if s["digest_daily_enabled"]:
            rows.append([InlineKeyboardButton(
                text=t(lang, f"Время сводки: {s['digest_daily_hour']:02d}:00", f"Digest time: {s['digest_daily_hour']:02d}:00"),
                callback_data="dlv:pick:dh",
            )])
    rows.append([InlineKeyboardButton(
        text=t(lang, "🌙 Ночной режим: ", "🌙 Night mode: ") + _on_off(s["night_mode_enabled"], lang),
        callback_data="dlv:night",
    )])
    if s["night_mode_enabled"]:
        rows.append([
            InlineKeyboardButton(text=t(lang, f"С {s['night_start_hour']:02d}:00", f"From {s['night_start_hour']:02d}:00"), callback_data="dlv:pick:ns"),
            InlineKeyboardButton(text=t(lang, f"До {s['night_end_hour']:02d}:00", f"To {s['night_end_hour']:02d}:00"), callback_data="dlv:pick:ne"),
        ])
    rows.append(_back_row(lang))
    return text, _kb(rows)


async def _show_delivery(query: CallbackQuery, toast: str | None = None) -> None:
    lang = await _lang_of(query)
    text, kb = await render_delivery(query.from_user.id, lang)
    await _edit_or_send(query, text, kb)
    await query.answer(toast)


async def cb_delivery(query: CallbackQuery) -> None:
    await _show_delivery(query)


async def cb_delivery_action(query: CallbackQuery) -> None:
    """dlv:mode:<m> | dlv:daily | dlv:night | dlv:pick:<f> | dlv:set:<f>:<h> | dlv:clear[:yes]"""
    lang = await _lang_of(query)
    uid = query.from_user.id
    parts = (query.data or "").split(":")
    action = parts[1] if len(parts) > 1 else ""
    saved = t(lang, "Сохранено", "Saved")

    if action == "mode" and len(parts) == 3 and parts[2] in ("instant", "digest"):
        cur = await repository.get_delivery_settings(uid)
        changes: dict[str, Any] = {"delivery_mode": parts[2]}
        # Как в Mini App: при первом переключении на digest включаем ежедневную сводку.
        if parts[2] == "digest" and cur["delivery_mode"] == "instant":
            changes["digest_daily_enabled"] = True
        await _save_delivery(uid, **changes)
        await _show_delivery(query, saved)
    elif action == "daily":
        cur = await repository.get_delivery_settings(uid)
        await _save_delivery(uid, digest_daily_enabled=not cur["digest_daily_enabled"])
        await _show_delivery(query, saved)
    elif action == "night":
        cur = await repository.get_delivery_settings(uid)
        await _save_delivery(uid, night_mode_enabled=not cur["night_mode_enabled"])
        await _show_delivery(query, saved)
    elif action == "pick" and len(parts) == 3 and parts[2] in _HOUR_FIELDS:
        field = parts[2]
        title = {
            "dh": t(lang, "Во сколько присылать сводку?", "When should the digest arrive?"),
            "ns": t(lang, "С какого часа ночной режим?", "Night mode starts at?"),
            "ne": t(lang, "До какого часа ночной режим?", "Night mode ends at?"),
        }[field]
        rows = [
            [InlineKeyboardButton(text=f"{h:02d}:00", callback_data=f"dlv:set:{field}:{h}") for h in range(r, r + 6)]
            for r in range(0, 24, 6)
        ]
        rows.append(_back_row(lang, CB_DELIVERY))
        await _edit_or_send(query, f"🕐 <b>{title}</b>\n" + t(lang, "Время московское.", "Moscow time."), _kb(rows))
        await query.answer()
    elif action == "set" and len(parts) == 4 and parts[2] in _HOUR_FIELDS and parts[3].isdigit() and 0 <= int(parts[3]) <= 23:
        await _save_delivery(uid, **{_HOUR_FIELDS[parts[2]]: int(parts[3])})
        await _show_delivery(query, saved)
    elif action == "clear" and len(parts) == 2:
        pending = await repository.count_pending(uid)
        rows = [
            [InlineKeyboardButton(text=t(lang, "🗑 Да, очистить", "🗑 Yes, clear"), callback_data="dlv:clear:yes")],
            _back_row(lang, CB_DELIVERY),
        ]
        await _edit_or_send(query, t(
            lang,
            f"Удалить <b>{pending}</b> накопленных объявлений без отправки?",
            f"Delete <b>{pending}</b> collected postings without sending them?",
        ), _kb(rows))
        await query.answer()
    elif action == "clear" and parts[2:] == ["yes"]:
        n = await repository.clear_pending(uid)
        await _show_delivery(query, t(lang, f"Удалено: {n}", f"Deleted: {n}"))
    else:
        await query.answer()


# ---------------------------------------------------------------- Чёрный список

async def render_blacklist(user_id: int, lang: Lang) -> tuple[str, InlineKeyboardMarkup]:
    words = await repository.get_user_blacklist(user_id)
    text = tge(E_BAN, "🚫") + t(lang, " <b>Чёрный список слов</b>\n\n", " <b>Blocked words</b>\n\n")
    text += t(
        lang,
        "Объявления, где встречаются эти слова или фразы, не будут приходить.\n\n",
        "Postings containing these words or phrases won't be sent to you.\n\n",
    )
    if words:
        text += ", ".join(f"<code>{html.escape(w)}</code>" for w in words)
        if len(words) > BL_BUTTONS_SHOWN:
            text += t(lang, f"\n\nКнопками можно удалить первые {BL_BUTTONS_SHOWN}.",
                      f"\n\nButtons below remove the first {BL_BUTTONS_SHOWN}.")
    else:
        text += t(lang, "Список пуст.", "The list is empty.")

    rows: list[list[InlineKeyboardButton]] = [[InlineKeyboardButton(
        text=t(lang, "➕ Добавить слова", "➕ Add words"), callback_data="bl:add",
    )]]
    word_btns = [
        InlineKeyboardButton(text=f"✕ {w}"[:40], callback_data=f"bl:rm:{i}")
        for i, w in enumerate(words[:BL_BUTTONS_SHOWN])
    ]
    rows += [word_btns[i:i + 2] for i in range(0, len(word_btns), 2)]
    if words:
        rows.append([InlineKeyboardButton(text=t(lang, "🗑 Очистить всё", "🗑 Clear all"), callback_data="bl:clear")])
    rows.append(_back_row(lang))
    return text, _kb(rows)


async def cb_blacklist(query: CallbackQuery) -> None:
    lang = await _lang_of(query)
    text, kb = await render_blacklist(query.from_user.id, lang)
    await _edit_or_send(query, text, kb)
    await query.answer()


async def cb_blacklist_action(query: CallbackQuery, state: FSMContext) -> None:
    lang = await _lang_of(query)
    uid = query.from_user.id
    parts = (query.data or "").split(":")
    action = parts[1] if len(parts) > 1 else ""
    if action == "add":
        await state.set_state(Input.blacklist_add)
        await _edit_or_send(query, t(
            lang,
            "✍️ Пришли слова или фразы, которые нужно исключить — через запятую или каждую с новой строки.\n\n"
            "Например: <code>курьер, без оплаты, 18+</code>",
            "✍️ Send the words or phrases to block — comma-separated or one per line.\n\n"
            "For example: <code>courier, unpaid, 18+</code>",
        ), _kb([[InlineKeyboardButton(text=t(lang, "Отмена", "Cancel"), callback_data=CB_BLACKLIST)]]))
        await query.answer()
        return
    if action == "rm" and len(parts) == 3 and parts[2].isdigit():
        words = await repository.get_user_blacklist(uid)
        i = int(parts[2])
        if 0 <= i < len(words):
            del words[i]
            await repository.set_user_blacklist(uid, words)
    elif action == "clear":
        await repository.set_user_blacklist(uid, [])
    text, kb = await render_blacklist(uid, lang)
    await _edit_or_send(query, text, kb)
    await query.answer(t(lang, "Сохранено", "Saved"))


async def msg_blacklist_add(message: Message, state: FSMContext) -> None:
    lang = await _lang_of_message(message)
    if not message.text:
        await message.answer(t(lang, "Пришли слова текстом.", "Please send the words as text."))
        return
    new = [w.strip() for w in re.split(r"[,;\n]", message.text) if w.strip()]
    new = [w[:100] for w in new]
    words = await repository.get_user_blacklist(message.from_user.id)  # type: ignore[union-attr]
    saved = await repository.set_user_blacklist(message.from_user.id, (words + new)[:BLACKLIST_MAX])  # type: ignore[union-attr]
    await state.clear()
    added = len(saved) - len(words)
    text, kb = await render_blacklist(message.from_user.id, lang)  # type: ignore[union-attr]
    await message.answer(
        t(lang, f"✅ Добавлено: {added}\n\n", f"✅ Added: {added}\n\n") + text,
        parse_mode="HTML", reply_markup=kb,
    )


# ---------------------------------------------------------------- Предложить канал / проблема

def _normalize_channel_ref(ref: str) -> tuple[str, str]:
    """(display_url, short_ref) — как в api.main._normalize_channel_url."""
    cleaned = ref.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    cleaned = cleaned.strip("/")
    if cleaned.startswith("c/"):
        chat_part = cleaned[2:].split("/", 1)[0]
        return f"https://t.me/c/{chat_part}", f"c/{chat_part}"
    cleaned = cleaned.lstrip("@").split("/", 1)[0]
    return f"https://t.me/{cleaned}", cleaned


_CHANNEL_REF_RE = re.compile(r"^(?:@[A-Za-z][A-Za-z0-9_]{3,}|(?:https?://)?t\.me/\S+)$", re.I)


async def _lang_of_message(message: Message) -> Lang:
    from bot import i18n
    u = message.from_user
    return await i18n.get_lang(u.id if u else 0, u.language_code if u else None)


def _cancel_kb(lang: Lang) -> InlineKeyboardMarkup:
    return _kb([[InlineKeyboardButton(text=t(lang, "Отмена", "Cancel"), callback_data=CB_MAIN)]])


def _done_kb(lang: Lang) -> InlineKeyboardMarkup:
    return _kb([[InlineKeyboardButton(text=t(lang, "🏠 В главное меню", "🏠 Main menu"), callback_data=CB_MAIN)]])


async def cb_suggest(query: CallbackQuery, state: FSMContext) -> None:
    lang = await _lang_of(query)
    await state.set_state(Input.suggest_channel)
    await _edit_or_send(query, tge(E_MEGAPHONE, "📣") + t(
        lang,
        " <b>Предложить канал</b>\n\nПришли ссылку на канал или его @username — админ посмотрит и добавит в мониторинг. "
        "После ссылки можно написать комментарий.\n\nНапример: <code>@kastingi_msk отличные массовки</code>",
        " <b>Suggest a channel</b>\n\nSend a channel link or @username — the admin will review it. "
        "You can add a comment after the link.\n\nFor example: <code>@kastingi_msk great extras gigs</code>",
    ), _cancel_kb(lang))
    await query.answer()


async def msg_suggest(message: Message, state: FSMContext) -> None:
    lang = await _lang_of_message(message)
    tokens = (message.text or "").strip().split(maxsplit=1)
    first = tokens[0] if tokens else ""
    comment = tokens[1] if len(tokens) > 1 else ""
    if not _CHANNEL_REF_RE.match(first) or len(first) > 200:
        await message.answer(t(
            lang,
            "Не похоже на ссылку на канал. Пришли @username или ссылку вида t.me/…",
            "That doesn't look like a channel link. Send an @username or a t.me/… link.",
        ), reply_markup=_cancel_kb(lang))
        return
    display_url, ref_short = _normalize_channel_ref(first)
    u = message.from_user
    user_link = f"https://t.me/{u.username}" if u and u.username else f"tg://user?id={u.id if u else 0}"
    user_label = f"@{u.username}" if u and u.username else f"id {u.id if u else 0}"
    comment = comment.strip()[:500]
    text = (
        "📨 <b>Новое предложение канала</b>\n\n"
        f"<b>Канал:</b> <a href=\"{html.escape(display_url)}\">{html.escape(display_url)}</a>\n"
        f"<b>От:</b> <a href=\"{html.escape(user_link)}\">{html.escape(user_label)}</a>"
        + (f"\n<i>Комментарий:</i> {html.escape(comment)}" if comment else "")
    )
    cb_safe = ref_short[:50]
    kb = _kb([[
        InlineKeyboardButton(text="✅ Добавить", callback_data=f"csg:add:{cb_safe}"),
        InlineKeyboardButton(text="❌ Не добавлять", callback_data=f"csg:skip:{cb_safe}"),
    ]])
    for admin_id in settings.admin_ids:
        try:
            await message.bot.send_message(admin_id, text, parse_mode="HTML", reply_markup=kb,  # type: ignore[union-attr]
                                           disable_web_page_preview=True)
        except Exception as e:  # noqa: BLE001
            logger.warning("channel suggestion notify admin {} failed: {}", admin_id, e)
    await state.clear()
    await message.answer(t(lang, "✅ Спасибо! Передали канал админу.", "✅ Thanks! The channel was sent to the admin."),
                         reply_markup=_done_kb(lang))


async def cb_problem(query: CallbackQuery, state: FSMContext) -> None:
    lang = await _lang_of(query)
    await state.set_state(Input.report_problem)
    await _edit_or_send(query, tge(E_WARN, "⚠️") + t(
        lang,
        " <b>Сообщить о проблеме</b>\n\nОпиши одним сообщением, что пошло не так — мы разберёмся.",
        " <b>Report a problem</b>\n\nDescribe what went wrong in one message — we'll look into it.",
    ), _cancel_kb(lang))
    await query.answer()


async def msg_problem(message: Message, state: FSMContext) -> None:
    lang = await _lang_of_message(message)
    body = (message.text or message.caption or "").strip()
    if len(body) < 3:
        await message.answer(t(lang, "Опиши проблему текстом (хотя бы пару слов).",
                               "Please describe the problem in text (at least a few words)."),
                             reply_markup=_cancel_kb(lang))
        return
    body = body[:2000]
    u = message.from_user
    p = await repository.create_problem(u.id, body)  # type: ignore[union-attr]
    handle = f"@{u.username}" if u and u.username else f"user #{u.id if u else 0}"
    admin_text = (
        f"🛟 <b>Новая проблема #{p.id}</b>\n"
        f"От: <b>{html.escape(handle)}</b> (id <code>{u.id if u else 0}</code>)\n\n"
        f"{html.escape(body[:1500])}"
    )
    kb = _kb(keyboards.problem_resolve_row(p.id))
    for admin_id in settings.admin_ids:
        try:
            await message.bot.send_message(admin_id, admin_text, parse_mode="HTML", reply_markup=kb)  # type: ignore[union-attr]
        except Exception as e:  # noqa: BLE001
            logger.warning("problem notify admin {} failed: {}", admin_id, e)
    await state.clear()
    await message.answer(t(lang, "✅ Спасибо! Передали админу, скоро разберёмся.",
                           "✅ Thanks! We've passed it to the admin and will look into it."),
                         reply_markup=_done_kb(lang))


# ---------------------------------------------------------------- Router

def build_router() -> Router:
    router = Router(name="settings_menu")
    router.callback_query.register(cb_favs, F.data == CB_FAVS)
    router.callback_query.register(cb_favs_retention, F.data == "favs:ret")
    router.callback_query.register(cb_favs_show, F.data.startswith("favs:show:"))
    router.callback_query.register(cb_delivery, F.data == CB_DELIVERY)
    router.callback_query.register(cb_delivery_action, F.data.startswith("dlv:"))
    router.callback_query.register(cb_blacklist, F.data == CB_BLACKLIST)
    router.callback_query.register(cb_blacklist_action, F.data.startswith("bl:"))
    router.callback_query.register(cb_suggest, F.data == CB_SUGGEST)
    router.callback_query.register(cb_problem, F.data == CB_PROBLEM)
    router.message.register(msg_blacklist_add, StateFilter(Input.blacklist_add))
    router.message.register(msg_suggest, StateFilter(Input.suggest_channel))
    router.message.register(msg_problem, StateFilter(Input.report_problem))
    return router
