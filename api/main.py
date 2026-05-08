"""FastAPI-приложение для Mini App."""
from __future__ import annotations

import sys

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
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
    GeneralProfileSchema,
    ProfileResponse,
    ProfileUpdate,
    SubscriptionPatchRequest,
    SubscriptionsCreateRequest,
    SuggestionsResponse,
)
from config import settings
from db import repository as repo

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
    """Кто я + админ ли + список подписок на категории."""
    subscriptions = await repo.get_subscriptions(user.id)
    return {
        "user_id": user.id,
        "username": user.username,
        "is_admin": is_admin_user(user),
        "subscriptions": subscriptions,
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
    return DeliverySettingsResponse(**s)


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
    return DeliverySettingsResponse(**saved)


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
