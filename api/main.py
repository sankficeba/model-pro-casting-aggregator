"""FastAPI-приложение для Mini App."""
from __future__ import annotations

import sys

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from api import admin as admin_module
from api import profile_repo
from api.auth import TelegramUser, current_user, is_admin_user
from api.reference_data import all_refs
from api.schemas import (
    AdminProfileSchema,
    BlacklistResponse,
    BlacklistUpdate,
    ChannelSuggestionRequest,
    CreativeProfileSchema,
    DeliverySettingsResponse,
    DeliverySettingsUpdate,
    DigestStartResponse,
    EventProfileSchema,
    FavoriteItem,
    FavoriteShowResponse,
    FavoritesListResponse,
    FavoritesSettings,
    PerfEvent,
    GeneralProfileSchema,
    ProblemActionResponse,
    ProblemItem,
    ProblemReportRequest,
    ProblemsListResponse,
    ProfileResponse,
    ProfileUpdate,
    SubscriptionCheckoutRequest,
    SubscriptionCheckoutResponse,
    SubscriptionPatchRequest,
    SubscriptionStatusResponse,
    SubscriptionsCreateRequest,
    SuggestionsResponse,
)
from config import settings
from db import repository as repo
from payments import yookassa_client

CATEGORY_TO_SCHEMA = {
    "creative": CreativeProfileSchema,
    "event": EventProfileSchema,
    "general": GeneralProfileSchema,
    "admin": AdminProfileSchema,
}

CATEGORY_LABELS = {
    "creative": "Творческие позиции",
    "event": "Event-персонал",
    "general": "Разнорабочие",
    "admin": "Администрирование",
}

FIRST_COMPLETION_MESSAGE = (
    "✅ Анкета успешно заполнена. "
    "Теперь вам будут поступать подходящие кастинги."
)
RECOMPLETION_MESSAGE = (
    "✏️ Анкета успешно изменена. Подборка кастингов обновлена."
)


def _category_completion_text(category: str, was_first_time: bool) -> str:
    label = CATEGORY_LABELS.get(category, category)
    if was_first_time:
        return (
            f"✅ Анкета «{label}» успешно заполнена. "
            "Теперь вам будут поступать подходящие вакансии."
        )
    return (
        f"✏️ Анкета «{label}» успешно изменена. "
        "Подборка вакансий обновлена."
    )


def _category_toggle_text(category: str, enabled: bool) -> str:
    label = CATEGORY_LABELS.get(category, category)
    if enabled:
        return (
            f"🔔 Категория «{label}» включена. "
            "Подходящие вакансии снова будут приходить в уведомлениях."
        )
    return (
        f"🔕 Категория «{label}» отключена. "
        "Уведомления по ней не будут приходить, пока не включишь обратно."
    )


async def _notify_user(chat_id: int, text: str) -> None:
    """Отправить пользователю сообщение через Bot API."""
    url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json={"chat_id": chat_id, "text": text})
            if r.status_code != 200:
                logger.warning(
                    "sendMessage failed for {}: {} {}",
                    chat_id, r.status_code, r.text,
                )
    except httpx.HTTPError as e:
        logger.warning("sendMessage error for {}: {}", chat_id, e)


async def _notify_admin_html(chat_id: int, text: str, reply_markup: dict | None = None) -> None:
    """Отправить админу HTML-сообщение с опциональной inline-клавиатурой."""
    url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload)
            if r.status_code != 200:
                logger.warning(
                    "admin sendMessage failed for {}: {} {}",
                    chat_id, r.status_code, r.text,
                )
    except httpx.HTTPError as e:
        logger.warning("admin sendMessage error for {}: {}", chat_id, e)


def _setup_logging() -> None:
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level.upper())


_setup_logging()

app = FastAPI(
    title="Casting Mini App API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

# CORS — Mini App грузится с того же домена, что и API (через Caddy),
# но при локальной разработке фронт может крутиться на vite-dev-server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # в проде Caddy всё равно один origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(admin_module.router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/me")
async def me(user: TelegramUser = Depends(current_user)) -> dict:
    """Кто я + админ ли + список подписок на категории.
    `bot_chat_active=false` сигнализирует фронту что юзер не нажимал /start
    в боте (или заблокировал/удалил его) — нотификации не доходят, нужно
    показать плашку с инструкцией."""
    subscriptions = await repo.get_subscriptions(user.id)
    db_user = await repo.get_user_by_id(user.id)
    bot_chat_active = bool(getattr(db_user, "bot_chat_active", True))
    return {
        "user_id": user.id,
        "username": user.username,
        "is_admin": is_admin_user(user),
        "subscriptions": subscriptions,
        "bot_chat_active": bot_chat_active,
    }


@app.get("/api/refs")
async def refs() -> dict:
    """Все справочники одним запросом — фронт кеширует на сессию."""
    return all_refs()


@app.get("/api/profile", response_model=ProfileResponse)
async def get_my_profile(user: TelegramUser = Depends(current_user)) -> ProfileResponse:
    p = await profile_repo.get_profile(user.id)
    if p is None:
        # Возвращаем «пустой» профиль, чтобы фронт мог отрисовать форму
        return ProfileResponse(user_id=user.id, completion_pct=0)
    return p


@app.put("/api/profile", response_model=ProfileResponse)
async def update_my_profile(
    data: ProfileUpdate,
    user: TelegramUser = Depends(current_user),
) -> ProfileResponse:
    return await profile_repo.upsert_profile(user.id, user.username, data)


@app.post("/api/profile/complete", response_model=ProfileResponse)
async def complete_my_profile(
    user: TelegramUser = Depends(current_user),
) -> ProfileResponse:
    """Финальное завершение анкеты: уведомляем пользователя в боте.

    Текст сообщения отличается в первый раз и при повторном завершении.
    """
    p, was_first_time = await profile_repo.mark_completed(user.id)
    if p is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Профиль не найден",
        )
    text = FIRST_COMPLETION_MESSAGE if was_first_time else RECOMPLETION_MESSAGE
    await _notify_user(user.id, text)
    return p


# ====================================================================
# Per-category subscriptions and profiles (mini-app categories feature)
# ====================================================================


@app.post("/api/subscriptions")
async def create_subscriptions(
    body: SubscriptionsCreateRequest,
    user: TelegramUser = Depends(current_user),
) -> dict:
    """Создать строки подписки. Идемпотентно. Возвращает обновлённый список."""
    subs = await repo.set_subscriptions(user.id, list(body.categories))
    return {"subscriptions": subs}


@app.patch("/api/subscriptions/{category}")
async def patch_subscription(
    category: str,
    body: SubscriptionPatchRequest,
    user: TelegramUser = Depends(current_user),
) -> dict:
    """Поменять enabled на категории."""
    if category not in CATEGORY_TO_SCHEMA:
        raise HTTPException(status_code=400, detail="Unknown category")
    ok = await repo.toggle_subscription(user.id, category, body.enabled)
    if not ok:
        raise HTTPException(status_code=404, detail="Subscription not found")
    await _notify_user(user.id, _category_toggle_text(category, body.enabled))
    return {"ok": True}


@app.get("/api/profile/suggestions", response_model=SuggestionsResponse)
async def profile_suggestions(
    user: TelegramUser = Depends(current_user),
) -> SuggestionsResponse:
    """Autocomplete-подсказки: значения, ранее введённые юзером в одноимённых полях
    других своих профилей."""
    suggestions = await repo.get_suggestions(user.id)
    return SuggestionsResponse(suggestions=suggestions)


@app.get("/api/profile/{category}")
async def get_category_profile_endpoint(
    category: str,
    user: TelegramUser = Depends(current_user),
) -> dict:
    """Профиль категории или пустой объект если не создан."""
    if category not in CATEGORY_TO_SCHEMA:
        raise HTTPException(status_code=400, detail="Unknown category")
    p = await repo.get_category_profile(user.id, category)
    return p or {"user_id": user.id, "category": category}


@app.put("/api/profile/{category}")
async def upsert_category_profile_endpoint(
    category: str,
    body: dict,
    user: TelegramUser = Depends(current_user),
) -> dict:
    """Draft-сохранение. Валидация Pydantic, но без проверки completeness."""
    if category not in CATEGORY_TO_SCHEMA:
        raise HTTPException(status_code=400, detail="Unknown category")
    schema_cls = CATEGORY_TO_SCHEMA[category]
    validated = schema_cls.model_validate(body)
    p = await repo.upsert_category_profile(
        user.id, category, validated.model_dump(exclude_unset=True)
    )
    return p or {}


@app.post("/api/profile/{category}/complete")
async def complete_category_profile_endpoint(
    category: str,
    user: TelegramUser = Depends(current_user),
) -> dict:
    """Финальное завершение анкеты категории — шлёт уведомление в бот."""
    if category not in CATEGORY_TO_SCHEMA:
        raise HTTPException(status_code=400, detail="Unknown category")
    p, was_first_time = await repo.complete_category_profile(user.id, category)
    if p is None:
        raise HTTPException(status_code=400, detail="Profile not found")
    await _notify_user(user.id, _category_completion_text(category, was_first_time))
    return p


# ---------- Blacklist ----------


@app.get("/api/blacklist", response_model=BlacklistResponse)
async def get_blacklist(user: TelegramUser = Depends(current_user)) -> BlacklistResponse:
    words = await repo.get_user_blacklist(user.id)
    return BlacklistResponse(words=words)


@app.put("/api/blacklist", response_model=BlacklistResponse)
async def update_blacklist(
    body: BlacklistUpdate,
    user: TelegramUser = Depends(current_user),
) -> BlacklistResponse:
    saved = await repo.set_user_blacklist(user.id, body.words)
    return BlacklistResponse(words=saved)


# ---------- Channel suggestion ----------


def _normalize_channel_url(ref: str) -> tuple[str, str]:
    """Из строки ref вытащить (display_label, callback_ref).
    callback_ref передаётся в callback_data — должен влезть в 64 байта,
    поэтому берём username или числовой id, без https://t.me/ префикса."""
    s = ref.strip()
    # Принимаем https://t.me/username, t.me/username, @username, https://t.me/c/<id>[/...]
    cleaned = s
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    cleaned = cleaned.strip("/")
    if cleaned.startswith("c/"):
        chat_part = cleaned[2:].split("/", 1)[0]
        return f"https://t.me/c/{chat_part}", f"c/{chat_part}"
    cleaned = cleaned.lstrip("@")
    return f"https://t.me/{cleaned}", cleaned


@app.post("/api/channel-suggestion")
async def channel_suggestion(
    body: ChannelSuggestionRequest,
    user: TelegramUser = Depends(current_user),
) -> dict:
    """Юзер предлагает канал админу. Шлёт всем админам HTML-сообщение
    с двумя inline-кнопками (Добавить / Не добавлять)."""
    display_url, ref_short = _normalize_channel_url(body.ref)
    user_link = (
        f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
    )
    user_label = f"@{user.username}" if user.username else f"id {user.id}"
    comment_block = (
        f"\n<i>Комментарий:</i> {body.comment}" if body.comment else ""
    )
    text = (
        f"📨 <b>Новое предложение канала</b>\n\n"
        f"<b>Канал:</b> <a href=\"{display_url}\">{display_url}</a>\n"
        f"<b>От:</b> <a href=\"{user_link}\">{user_label}</a>"
        f"{comment_block}"
    )

    # callback_data ограничен 64 байтами. ref_short может быть длинным
    # username — обрежем до безопасного размера. Если не влезает в
    # callback — приложим к тексту, чтобы админ мог скопировать вручную.
    cb_safe = ref_short[:50]  # запас на префикс "csg:add:"
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Добавить", "callback_data": f"csg:add:{cb_safe}"},
                {"text": "❌ Не добавлять", "callback_data": f"csg:skip:{cb_safe}"},
            ]
        ]
    }
    sent = 0
    for admin_id in settings.admin_ids:
        await _notify_admin_html(admin_id, text, reply_markup)
        sent += 1
    return {"ok": True, "notified_admins": sent}


# ---------- Delivery settings ----------


@app.get("/api/delivery-settings", response_model=DeliverySettingsResponse)
async def get_delivery(user: TelegramUser = Depends(current_user)) -> DeliverySettingsResponse:
    s = await repo.get_delivery_settings(user.id)
    pending_count = await repo.count_pending(user.id)
    return DeliverySettingsResponse(**s, pending_count=pending_count)


@app.put("/api/delivery-settings", response_model=DeliverySettingsResponse)
async def put_delivery(
    body: DeliverySettingsUpdate,
    user: TelegramUser = Depends(current_user),
) -> DeliverySettingsResponse:
    saved = await repo.set_delivery_settings(
        user.id,
        delivery_mode=body.delivery_mode,
        night_mode_enabled=body.night_mode_enabled,
        night_start_hour=body.night_start_hour,
        night_end_hour=body.night_end_hour,
        digest_daily_enabled=body.digest_daily_enabled,
        digest_daily_hour=body.digest_daily_hour,
    )
    pending_count = await repo.count_pending(user.id)
    return DeliverySettingsResponse(**saved, pending_count=pending_count)


@app.post("/api/digest/start", response_model=DigestStartResponse)
async def digest_start(
    user: TelegramUser = Depends(current_user),
) -> DigestStartResponse:
    """Кнопка «Пролистать накопленные» в Mini App: достаёт следующее
    pending-уведомление и шлёт пользователю. Дальше юзер листает кнопкой
    «Следующее» в чате с ботом."""
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    from bot.handlers import _send_next_pending

    bot = Bot(
        settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        sent = await _send_next_pending(bot, user.id)
    finally:
        await bot.session.close()
    remaining = await repo.count_pending(user.id)
    return DigestStartResponse(sent=sent, remaining=remaining)


# ---------- Subscription / payments ----------


@app.get("/api/subscription/status", response_model=SubscriptionStatusResponse)
async def subscription_status(
    user: TelegramUser = Depends(current_user),
) -> SubscriptionStatusResponse:
    s = await repo.get_subscription_status(user.id)
    from api.plans import SUBSCRIPTION_PLANS, get_plan
    default_plan = get_plan(None)
    return SubscriptionStatusResponse(
        active_until=s["active_until"],
        days_left=s["days_left"],
        is_active=s["is_active"],
        trial_started_at=s["trial_started_at"],
        plan_price_rub=default_plan.price_rub,
        plan_period_days=default_plan.days,
        payments_configured=yookassa_client.is_configured(),
        plans=SUBSCRIPTION_PLANS,
    )


@app.post("/api/subscription/checkout", response_model=SubscriptionCheckoutResponse)
async def subscription_checkout(
    body: SubscriptionCheckoutRequest = SubscriptionCheckoutRequest(),
    user: TelegramUser = Depends(current_user),
) -> SubscriptionCheckoutResponse:
    """Создать YooKassa-платёж по выбранному тарифу. Если plan_code пуст,
    используется тариф по умолчанию (1 месяц)."""
    if not yookassa_client.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Платёжная система не настроена. Свяжись с администратором.",
        )
    import uuid

    from api.plans import get_plan
    plan = get_plan(body.plan_code)
    days = plan.days
    amount_rub = plan.price_rub
    idempotency_key = uuid.uuid4().hex
    payment_id = await repo.insert_payment_pending(
        user_id=user.id,
        idempotency_key=idempotency_key,
        amount_rub=amount_rub,
        days=days,
    )
    base_return = settings.subscription_return_url or "https://t.me/"
    # Маркер ?paid=1 нужен чтобы Mini App после редиректа понял, что юзер
    # только что оплатил и показал toast «Подписка активирована».
    sep = "&" if "?" in base_return else "?"
    return_url = f"{base_return}{sep}paid=1"
    try:
        created = await yookassa_client.create_payment(
            amount_rub=amount_rub,
            days=days,
            user_id=user.id,
            idempotency_key=idempotency_key,
            return_url=return_url,
            description=f"Подписка: {plan.label}",
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("YooKassa create_payment failed: {}", e)
        raise HTTPException(
            status_code=502, detail="Не удалось создать платёж. Попробуй позже."
        ) from e
    await repo.attach_yk_payment_id(payment_id, created.payment_id)
    return SubscriptionCheckoutResponse(
        confirmation_url=created.confirmation_url,
        payment_id=created.payment_id,
    )


# ---------- Favorites ----------


def _favorite_keyboard_dict(message_id: int) -> dict:
    """JSON-структура inline-клавиатуры для пере-отправляемого избранного.
    Зеркалит bot/keyboards.actions_rows, но в виде dict (для httpx)."""
    from bot.keyboards import (
        EMOJI_DELETE, EMOJI_DETAILS, EMOJI_FAV_REMOVE,
    )
    return {
        "inline_keyboard": [
            [
                {"text": "Ссылка на группу",
                 "callback_data": f"details:{message_id}",
                 "icon_custom_emoji_id": EMOJI_DETAILS},
                {"text": "Удалить",
                 "callback_data": "delself:",
                 "icon_custom_emoji_id": EMOJI_DELETE},
            ],
            [
                {"text": "Удалить из избранного",
                 "callback_data": f"fav:rm:{message_id}",
                 "icon_custom_emoji_id": EMOJI_FAV_REMOVE},
            ],
        ]
    }


def _strip_html(text: str) -> str:
    """Дёшево убрать html-теги из notification_text для preview в Mini App."""
    import re
    no_tags = re.sub(r"<[^>]+>", "", text)
    return no_tags.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


async def _build_favorite_message(
    user_id: int, message_id: int, matched_vacancy_ids: list[int],
) -> tuple[str, dict] | None:
    """Собрать (notification_text, reply_markup) для пере-отправки в чат
    из избранного. Возвращает None если canonical Message исчез."""
    from bot.keyboards import EMOJI_RESPOND
    from db import matching
    from userbot.client import Userbot, _vacancy_title

    loaded = await repo.get_canonical_with_vacancies(message_id)
    if loaded is None:
        return None
    canon_msg, canon_vacancies = loaded
    post, vac_extractions = matching._orm_to_extractions(canon_msg, canon_vacancies)
    matched_set = set(matched_vacancy_ids or [])
    matched_idxs: list[int] = [
        i for i, v in enumerate(canon_vacancies) if v.id in matched_set
    ]
    if not matched_idxs:
        # Fallback: если ids потерялись, показываем все вакансии canonical.
        matched_idxs = list(range(len(canon_vacancies)))
    if not matched_idxs:
        return None
    eff_cat = (
        canon_vacancies[matched_idxs[0]].category if canon_vacancies else None
    ) or canon_msg.category

    class _PseudoMsg:
        id = canon_msg.tg_message_id
        message = canon_msg.text

    fallback_link = None
    if not canon_msg.tg_chat_username:
        fallback_link = await repo.get_message_permalink(message_id)
    text = Userbot._format_notification(
        post=post,
        vacancies=vac_extractions,
        matched_idxs=matched_idxs,
        message=_PseudoMsg(),
        chat_username=canon_msg.tg_chat_username,
        effective_category=eff_cat,
        invite_link=fallback_link,
    )

    # Кнопки: вакансии-отклики + 3-rd row из bot/keyboards (через dict).
    rows: list[list[dict]] = []
    for i in matched_idxs:
        v = canon_vacancies[i]
        title = _vacancy_title(vac_extractions[i])
        rows.append([{
            "text": f"Сгенерировать отклик: {title}"[:64],
            "callback_data": f"respond:{v.id}",
            "icon_custom_emoji_id": EMOJI_RESPOND,
        }])
    fav_kb = _favorite_keyboard_dict(message_id)
    rows += fav_kb["inline_keyboard"]
    return text, {"inline_keyboard": rows}


def _favorite_preview(text: str) -> tuple[str, str]:
    """(title, preview) из rendered notification text. title = первая
    непустая строка без HTML, preview = до 240 символов."""
    plain = _strip_html(text).strip()
    lines = [ln.strip() for ln in plain.split("\n") if ln.strip()]
    title = lines[0] if lines else "Без названия"
    preview = "\n".join(lines[:5])[:280]
    return title, preview


@app.get("/api/favorites", response_model=FavoritesListResponse)
async def list_favorites(
    user: TelegramUser = Depends(current_user),
) -> FavoritesListResponse:
    """Список избранных кастингов пользователя. Bulk-load по message_ids
    в 3 запроса (messages, vacancies, channels) вместо N×3 для каждого
    избранного — было ~10-15с при 28 избранных, стало ~200мс."""
    import time as _time
    from sqlalchemy import select as _select
    from db import matching
    from db.models import Channel, Message as MessageRow, Vacancy as VacancyRow
    from db.session import AsyncSessionLocal
    from userbot.client import Userbot, _vacancy_title  # noqa: F401

    t0 = _time.monotonic()
    # Авто-чистка по сроку retention перед выдачей списка.
    try:
        await repo.prune_old_favorites(user.id)
    except Exception:  # noqa: BLE001
        pass
    t1 = _time.monotonic()
    favs = await repo.list_favorites(user.id)
    t2 = _time.monotonic()
    if not favs:
        logger.info(
            "favorites user={} empty (prune={:.0f}ms list={:.0f}ms)",
            user.id, (t1 - t0) * 1000, (t2 - t1) * 1000,
        )
        return FavoritesListResponse(items=[])

    msg_ids = [f.message_id for f in favs]
    t_bulk_start = _time.monotonic()
    async with AsyncSessionLocal() as session:
        msgs_res = await session.execute(
            _select(MessageRow).where(MessageRow.id.in_(msg_ids))
        )
        msgs_by_id: dict[int, MessageRow] = {m.id: m for m in msgs_res.scalars()}

        vacs_res = await session.execute(
            _select(VacancyRow)
            .where(VacancyRow.message_id.in_(msg_ids))
            .order_by(VacancyRow.idx)
        )
        vacs_by_msg: dict[int, list[VacancyRow]] = {}
        for v in vacs_res.scalars():
            vacs_by_msg.setdefault(v.message_id, []).append(v)

        chat_ids = sorted({
            m.tg_chat_id for m in msgs_by_id.values()
            if m.tg_chat_id is not None
        })
        channels_by_chat: dict[int, Channel] = {}
        if chat_ids:
            ch_res = await session.execute(
                _select(Channel).where(Channel.tg_chat_id.in_(chat_ids))
            )
            for c in ch_res.scalars():
                channels_by_chat[c.tg_chat_id] = c
    t_bulk_end = _time.monotonic()

    def _source_label(msg: MessageRow) -> str:
        if msg.tg_chat_username:
            return f"@{msg.tg_chat_username}"
        if msg.tg_chat_id is not None:
            ch = channels_by_chat.get(msg.tg_chat_id)
            if ch is not None and ch.username:
                return f"@{ch.username}"
            if ch is not None:
                return f"приватный канал #{ch.id}"
        return "источник"

    items: list[FavoriteItem] = []
    for f in favs:
        msg = msgs_by_id.get(f.message_id)
        if msg is None:
            continue
        canon_vacancies = vacs_by_msg.get(f.message_id, [])
        if not canon_vacancies:
            continue
        post, vac_extractions = matching._orm_to_extractions(msg, canon_vacancies)
        matched_set = set(f.matched_vacancy_ids or [])
        matched_idxs = [
            i for i, v in enumerate(canon_vacancies) if v.id in matched_set
        ]
        if not matched_idxs:
            matched_idxs = list(range(len(canon_vacancies)))

        class _PseudoMsg:
            id = msg.tg_message_id
            message = msg.text

        eff_cat = (
            canon_vacancies[matched_idxs[0]].category if canon_vacancies else None
        ) or msg.category
        text = Userbot._format_notification(
            post=post,
            vacancies=vac_extractions,
            matched_idxs=matched_idxs,
            message=_PseudoMsg(),
            chat_username=msg.tg_chat_username,
            effective_category=eff_cat,
        )
        title, preview = _favorite_preview(text)
        items.append(FavoriteItem(
            message_id=f.message_id,
            title=title,
            preview=preview,
            saved_at=f.created_at,
            source_label=_source_label(msg),
        ))
    t_end = _time.monotonic()
    logger.info(
        "favorites user={} n={} (prune={:.0f}ms list={:.0f}ms bulk={:.0f}ms render={:.0f}ms total={:.0f}ms)",
        user.id, len(items),
        (t1 - t0) * 1000,
        (t2 - t1) * 1000,
        (t_bulk_end - t_bulk_start) * 1000,
        (t_end - t_bulk_end) * 1000,
        (t_end - t0) * 1000,
    )
    return FavoritesListResponse(items=items)


@app.delete("/api/favorites/{message_id}")
async def delete_favorite(
    message_id: int,
    user: TelegramUser = Depends(current_user),
) -> dict:
    ok = await repo.remove_favorite(user.id, message_id)
    return {"ok": ok}


@app.get("/api/favorites/settings", response_model=FavoritesSettings)
async def get_favorites_settings(
    user: TelegramUser = Depends(current_user),
) -> FavoritesSettings:
    days = await repo.get_favorites_retention_days(user.id)
    return FavoritesSettings(retention_days=days)


@app.put("/api/favorites/settings", response_model=FavoritesSettings)
async def put_favorites_settings(
    body: FavoritesSettings,
    user: TelegramUser = Depends(current_user),
) -> FavoritesSettings:
    ok = await repo.set_favorites_retention_days(user.id, body.retention_days)
    if not ok:
        raise HTTPException(status_code=400, detail="retention_days must be 0..90")
    return body


@app.post("/api/perf")
async def report_perf(
    body: PerfEvent,
    user: TelegramUser = Depends(current_user),
) -> dict:
    """Принимает клиентские perf-метрики из Mini App и логирует.
    Помогает понять что тормозит у конкретного юзера (network/render),
    когда total на бэкенде хороший, а юзер видит лаг."""
    parts_str = " ".join(f"{k}={v}ms" for k, v in (body.parts or {}).items())
    logger.info(
        "perf user={} event={} total={}ms {}{}",
        user.id, body.event, body.total_ms,
        parts_str,
        f" ua={body.user_agent[:60]}" if body.user_agent else "",
    )
    return {"ok": True}


@app.post("/api/favorites/{message_id}/show-in-chat", response_model=FavoriteShowResponse)
async def show_favorite_in_chat(
    message_id: int,
    user: TelegramUser = Depends(current_user),
) -> FavoriteShowResponse:
    """Переотправить избранную вакансию в чат бота. Mini App после успеха
    закрывается через Telegram.WebApp.close()."""
    fav = await repo.get_favorite(user.id, message_id)
    if fav is None:
        raise HTTPException(status_code=404, detail="Не в избранном")
    built = await _build_favorite_message(
        user.id, message_id, list(fav.matched_vacancy_ids or []),
    )
    if built is None:
        raise HTTPException(status_code=410, detail="Сообщение больше недоступно")
    text, markup = built
    url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                url,
                json={
                    "chat_id": user.id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                    "reply_markup": markup,
                },
            )
            if r.status_code != 200:
                logger.warning("Favorite show-in-chat send failed: {} {}",
                               r.status_code, r.text)
                return FavoriteShowResponse(sent=False, error=r.text)
    except httpx.HTTPError as e:
        logger.warning("Favorite show-in-chat HTTP error: {}", e)
        return FavoriteShowResponse(sent=False, error=str(e))
    return FavoriteShowResponse(sent=True)


# ---------- Problems ----------


def _problem_admin_text(problem_id: int, username: str | None, user_id: int, body: str) -> str:
    """HTML-текст уведомления админу о новой проблеме."""
    handle = f"@{username}" if username else f"user #{user_id}"
    safe = (body or "").replace("<", "&lt;").replace(">", "&gt;")[:1500]
    return (
        f"🛟 <b>Новая проблема #{problem_id}</b>\n"
        f"От: <b>{handle}</b> (id <code>{user_id}</code>)\n\n"
        f"{safe}"
    )


async def _send_problem_to_admins(problem_id: int, username: str | None, user_id: int, body: str) -> int:
    """Разослать всем админам нотификацию с кнопкой «Проблема решена».
    Возвращает кол-во доставленных."""
    from bot.keyboards import problem_resolve_dict
    text = _problem_admin_text(problem_id, username, user_id, body)
    markup = problem_resolve_dict(problem_id)
    delivered = 0
    for admin_id in settings.admin_ids:
        await _notify_admin_html(admin_id, text, reply_markup=markup)
        delivered += 1
    return delivered


@app.post("/api/problems", response_model=ProblemActionResponse)
async def report_problem(
    body: ProblemReportRequest,
    user: TelegramUser = Depends(current_user),
) -> ProblemActionResponse:
    p = await repo.create_problem(user.id, body.text.strip())
    try:
        await _send_problem_to_admins(p.id, user.username, user.id, p.text)
    except Exception as e:  # noqa: BLE001
        logger.warning("Problem admin notify failed: {}", e)
    return ProblemActionResponse(ok=True)


@app.get("/api/problems", response_model=ProblemsListResponse)
async def list_problems_admin(
    user: TelegramUser = Depends(current_user),
) -> ProblemsListResponse:
    if not is_admin_user(user):
        raise HTTPException(status_code=403, detail="forbidden")
    rows = await repo.list_active_problems()
    items: list[ProblemItem] = []
    for p in rows:
        u = await repo.get_user_by_id(p.user_id)
        items.append(ProblemItem(
            id=p.id,
            user_id=p.user_id,
            username=getattr(u, "username", None) if u else None,
            full_name=None,
            text=p.text,
            created_at=p.created_at,
        ))
    return ProblemsListResponse(items=items)


@app.post("/api/problems/{problem_id}/resolve", response_model=ProblemActionResponse)
async def resolve_problem_admin(
    problem_id: int,
    user: TelegramUser = Depends(current_user),
) -> ProblemActionResponse:
    if not is_admin_user(user):
        raise HTTPException(status_code=403, detail="forbidden")
    ok = await repo.resolve_problem(problem_id)
    return ProblemActionResponse(ok=ok)


@app.post("/api/problems/{problem_id}/show-in-chat", response_model=ProblemActionResponse)
async def show_problem_in_chat(
    problem_id: int,
    user: TelegramUser = Depends(current_user),
) -> ProblemActionResponse:
    """Переотправить тикет в чат админа (для удобства просмотра / закрытия)."""
    if not is_admin_user(user):
        raise HTTPException(status_code=403, detail="forbidden")
    p = await repo.get_problem(problem_id)
    if p is None:
        raise HTTPException(status_code=404, detail="not_found")
    reporter = await repo.get_user_by_id(p.user_id)
    text = _problem_admin_text(
        p.id,
        getattr(reporter, "username", None) if reporter else None,
        p.user_id,
        p.text,
    )
    from bot.keyboards import problem_resolve_dict
    url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json={
                "chat_id": user.id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "reply_markup": problem_resolve_dict(p.id),
            })
            if r.status_code != 200:
                logger.warning("Problem show-in-chat failed: {} {}", r.status_code, r.text)
                return ProblemActionResponse(ok=False, error=r.text)
    except httpx.HTTPError as e:
        return ProblemActionResponse(ok=False, error=str(e))
    return ProblemActionResponse(ok=True)


@app.post("/api/yookassa/webhook")
async def yookassa_webhook(request: Request) -> dict:
    """Webhook от YooKassa: payment.succeeded → продлеваем подписку.
    Защита: shared-secret в query (?token=...) + сверка payment_id с БД."""
    expected = settings.yookassa_webhook_token
    got = request.query_params.get("token", "")
    if expected and got != expected:
        raise HTTPException(status_code=403, detail="bad token")
    body = await request.body()
    parsed = yookassa_client.parse_webhook(body)
    if parsed is None:
        return {"ok": False, "reason": "parse_failed"}
    if parsed.get("event") != "payment.succeeded":
        return {"ok": True, "ignored": parsed.get("event")}
    yk_id = parsed.get("payment_id")
    if not yk_id:
        return {"ok": False, "reason": "no_payment_id"}
    payment = await repo.get_payment_by_yk_id(yk_id)
    if payment is None:
        # YK прислал событие на несуществующий платёж — игнор.
        logger.warning("Webhook for unknown payment_id: {}", yk_id)
        return {"ok": False, "reason": "unknown_payment"}
    should_extend = await repo.mark_payment_status(yk_id, "succeeded")
    if should_extend:
        new_until = await repo.extend_subscription(payment.user_id, payment.days)
        logger.info(
            "Subscription extended user={} payment={} active_until={}",
            payment.user_id, yk_id, new_until,
        )
        # Уведомим юзера в чате
        text = (
            "✅ <b>Подписка активна!</b>\n\n"
            f"Действует до <b>{new_until.strftime('%d.%m.%Y')}</b>. "
            "Спасибо!"
        )
        url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    url,
                    json={
                        "chat_id": payment.user_id,
                        "text": text,
                        "parse_mode": "HTML",
                    },
                )
        except httpx.HTTPError as e:
            logger.warning("Subscription confirmation send failed: {}", e)
    return {"ok": True}
