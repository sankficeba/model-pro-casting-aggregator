"""Главное меню бота и оплата подписки прямо в чате.

Любое сообщение юзера (кроме команд и админ-рассылки) отвечается главным
меню. Из него — выбор тарифа → ссылка на оплату ЮKassa. Продлевает
подписку тот же webhook, что и при оплате из Mini App.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from loguru import logger

from api.plans import PLAN_LABELS_EN, SUBSCRIPTION_PLANS, find_plan
from api.schemas import SubscriptionPlan
from bot import i18n
from bot.i18n import Lang, t
from config import settings
from db import repository
from payments import yookassa_client
from payments.checkout import create_subscription_payment

CB_MAIN = "menu:main"
CB_SUB = "sub:menu"
CB_PLAN_PREFIX = "sub:plan:"
CB_LANG_TOGGLE = "menu:lang"


def _days_ru(n: int) -> str:
    if 11 <= n % 100 <= 14:
        return "дней"
    return {1: "день", 2: "дня", 3: "дня", 4: "дня"}.get(n % 10, "дней")


def _plan_title(plan: SubscriptionPlan, lang: Lang) -> str:
    return PLAN_LABELS_EN.get(plan.code, plan.label) if lang == "en" else plan.label


def _plan_button_text(plan: SubscriptionPlan, lang: Lang) -> str:
    """«3 месяца — 799 ₽ · ≈266 ₽/мес»."""
    text = f"{_plan_title(plan, lang)} — {plan.price_rub} ₽"
    months = plan.days // 30
    if months > 1:
        per_month = round(plan.price_rub / months)
        text += t(lang, f" · ≈{per_month} ₽/мес", f" · ≈{per_month} ₽/mo")
    return text


async def _status_line(user_id: int, lang: Lang) -> tuple[str, bool]:
    s = await repository.get_subscription_status(user_id)
    if s["is_active"] and s["active_until"] is not None:
        days = s["days_left"]
        until_ru = s["active_until"].strftime("%d.%m.%Y")
        until_en = s["active_until"].strftime("%m/%d/%Y")
        return t(
            lang,
            f"✅ Подписка активна до <b>{until_ru}</b> (осталось {days} {_days_ru(days)})",
            f"✅ Subscription active until <b>{until_en}</b> ({days} day{'s' if days != 1 else ''} left)",
        ), True
    return t(
        lang,
        "❌ Подписка не активна — уведомления приходят в режиме «1 в день».",
        "❌ Subscription inactive — notifications arrive in \"1 per day\" mode.",
    ), False


async def build_main_menu(user_id: int, lang: Lang) -> tuple[str, InlineKeyboardMarkup]:
    status, active = await _status_line(user_id, lang)
    text = (
        t(lang, "🏠 <b>Главное меню</b>", "🏠 <b>Main menu</b>")
        + "\n\n<blockquote>"
        + t(
            lang,
            "Присылаем свежие кастинги и подработки по твоим направлениям первым. "
            "Анкету и настройки уведомлений меняй в Mini App.",
            "We send you fresh castings and gigs in your categories first. "
            "Edit your profile and notification settings in the Mini App.",
        )
        + "</blockquote>\n\n"
        + status
        + "\n"
        + t(
            lang,
            f"💰 Тариф — от {SUBSCRIPTION_PLANS[0].price_rub} ₽/мес",
            f"💰 Plans from {SUBSCRIPTION_PLANS[0].price_rub} ₽/mo",
        )
    )
    rows: list[list[InlineKeyboardButton]] = [[
        InlineKeyboardButton(
            text=t(lang, "💳 Продлить подписку", "💳 Renew subscription") if active
            else t(lang, "💳 Оформить подписку", "💳 Subscribe"),
            callback_data=CB_SUB,
        )
    ]]
    try:
        pending = await repository.count_pending(user_id)
    except Exception:  # noqa: BLE001
        pending = 0
    if pending > 0:
        rows.append([InlineKeyboardButton(
            text=t(lang, f"📬 Накопленные объявления ({pending})", f"📬 Saved postings ({pending})"),
            callback_data="digest:next",
        )])
    if settings.webapp_url.startswith("https://"):
        rows.append([InlineKeyboardButton(
            text=t(lang, "📱 Открыть приложение", "📱 Open app"),
            web_app=WebAppInfo(url=settings.webapp_url),
        )])
    rows.append([InlineKeyboardButton(
        text="🇬🇧 English" if lang == "ru" else "🇷🇺 Русский",
        callback_data=CB_LANG_TOGGLE,
    )])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


async def build_subscription_menu(user_id: int, lang: Lang) -> tuple[str, InlineKeyboardMarkup]:
    status, active = await _status_line(user_id, lang)
    title = (
        t(lang, "💳 <b>Продлить подписку</b>", "💳 <b>Renew subscription</b>") if active
        else t(lang, "💳 <b>Оформить подписку</b>", "💳 <b>Subscribe</b>")
    )
    text = (
        title + "\n\n" + status + "\n\n"
        + t(
            lang,
            "Выбери срок — оплата картой или по СБП через ЮKassa. "
            "Подписка продлится сразу после оплаты, дни добавятся к текущему сроку.",
            "Choose a duration — pay by card or SBP via YooKassa. "
            "The subscription is extended right after payment; days are added to your current term.",
        )
    )
    rows = [
        [InlineKeyboardButton(text=_plan_button_text(p, lang), callback_data=f"{CB_PLAN_PREFIX}{p.code}")]
        for p in SUBSCRIPTION_PLANS
    ]
    rows.append([InlineKeyboardButton(text=t(lang, "⬅️ Назад", "⬅️ Back"), callback_data=CB_MAIN)])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def subscribe_button_row(lang: Lang) -> list[InlineKeyboardButton]:
    """Кнопка «Продлить подписку» для напоминаний об истечении."""
    return [InlineKeyboardButton(
        text=t(lang, "💳 Продлить подписку", "💳 Renew subscription"),
        callback_data=CB_SUB,
    )]


async def send_main_menu(message: Message, lang: Lang) -> None:
    text, kb = await build_main_menu(message.from_user.id, lang)  # type: ignore[union-attr]
    await message.answer(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)


async def _edit_or_send(query: CallbackQuery, text: str, kb: InlineKeyboardMarkup) -> None:
    msg = query.message
    try:
        await msg.edit_text(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)  # type: ignore[union-attr]
    except Exception as e:  # noqa: BLE001
        if "message is not modified" in str(e):
            return
        # Сообщение слишком старое / не текстовое — шлём новое.
        if msg is not None:
            try:
                await msg.answer(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
            except Exception as e:  # noqa: BLE001
                logger.warning("menu send failed: {}", e)


async def _lang_of(query: CallbackQuery) -> Lang:
    u = query.from_user
    return await i18n.get_lang(u.id if u else 0, u.language_code if u else None)


def build_router() -> Router:
    """Новый Router на каждый Dispatcher (aiogram не даёт подключить один
    роутер к двум диспетчерам)."""
    router = Router(name="menu")
    router.callback_query.register(cb_main, F.data == CB_MAIN)
    router.callback_query.register(cb_lang_toggle, F.data == CB_LANG_TOGGLE)
    router.callback_query.register(cb_subscription, F.data == CB_SUB)
    router.callback_query.register(cb_plan, F.data.startswith(CB_PLAN_PREFIX))
    return router


async def cb_main(query: CallbackQuery) -> None:
    lang = await _lang_of(query)
    text, kb = await build_main_menu(query.from_user.id, lang)
    await _edit_or_send(query, text, kb)
    await query.answer()


async def cb_lang_toggle(query: CallbackQuery) -> None:
    lang: Lang = "en" if (await _lang_of(query)) == "ru" else "ru"
    await repository.set_user_language(query.from_user.id, lang)
    text, kb = await build_main_menu(query.from_user.id, lang)
    await _edit_or_send(query, text, kb)
    await query.answer()


async def cb_subscription(query: CallbackQuery) -> None:
    lang = await _lang_of(query)
    text, kb = await build_subscription_menu(query.from_user.id, lang)
    await _edit_or_send(query, text, kb)
    await query.answer()


async def cb_plan(query: CallbackQuery) -> None:
    lang = await _lang_of(query)
    plan = find_plan((query.data or "")[len(CB_PLAN_PREFIX):])
    if plan is None:
        await query.answer(t(lang, "Неизвестный тариф.", "Unknown plan."), show_alert=True)
        return
    if not yookassa_client.is_configured():
        await query.answer(
            t(lang, "Оплата временно недоступна. Напиши администратору.",
              "Payments are temporarily unavailable. Please contact the admin."),
            show_alert=True,
        )
        return
    await query.answer(t(lang, "Создаём ссылку на оплату…", "Creating a payment link…"))
    try:
        created = await create_subscription_payment(query.from_user.id, plan)
    except Exception as e:  # noqa: BLE001
        logger.exception("bot checkout failed user={} plan={}: {}", query.from_user.id, plan.code, e)
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t(lang, "⬅️ Назад", "⬅️ Back"), callback_data=CB_SUB),
        ]])
        await _edit_or_send(
            query,
            t(lang, "⚠️ Не удалось создать платёж. Попробуй ещё раз чуть позже.",
              "⚠️ Couldn't create the payment. Please try again a bit later."),
            kb,
        )
        return
    title = _plan_title(plan, lang)
    text = t(
        lang,
        f"📅 <b>Подписка на {title} — {plan.price_rub} ₽</b>\n\n"
        f"Нажми «Оплатить» — откроется страница ЮKassa (карта или СБП). "
        f"После оплаты подписка продлится на {plan.days} {_days_ru(plan.days)}, "
        f"а бот пришлёт подтверждение.",
        f"📅 <b>{title} subscription — {plan.price_rub} ₽</b>\n\n"
        f"Tap \"Pay\" to open the YooKassa page (card or SBP). "
        f"After payment the subscription is extended by {plan.days} days "
        f"and the bot will send a confirmation.",
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t(lang, f"💳 Оплатить {plan.price_rub} ₽", f"💳 Pay {plan.price_rub} ₽"),
            url=created.confirmation_url,
        )],
        [InlineKeyboardButton(text=t(lang, "⬅️ Другой тариф", "⬅️ Other plan"), callback_data=CB_SUB)],
    ])
    await _edit_or_send(query, text, kb)
