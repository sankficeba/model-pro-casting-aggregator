"""FastAPI-приложение для Mini App."""
from __future__ import annotations

import sys

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from api import admin as admin_module
from api.auth import TelegramUser, current_user, is_admin_user
from api.reference_data import all_refs
from api.schemas import (
    AdminProfileSchema,
    CreativeProfileSchema,
    DeliverySettingsResponse,
    DigestStartResponse,
    EventProfileSchema,
    GeneralProfileSchema,
    LanguageUpdate,
    ProblemActionResponse,
    ProblemItem,
    ProblemsListResponse,
    SubscriptionPatchRequest,
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
    import asyncio as _asyncio
    subscriptions, db_user = await _asyncio.gather(
        repo.get_subscriptions(user.id),
        repo.get_user_by_id(user.id),
    )
    bot_chat_active = bool(getattr(db_user, "bot_chat_active", True))
    return {
        "user_id": user.id,
        "username": user.username,
        "is_admin": is_admin_user(user),
        "subscriptions": subscriptions,
        "bot_chat_active": bot_chat_active,
        # Явный выбор языка (общий для бота и Mini App). None — не выбирал.
        "language": getattr(db_user, "language", None),
    }


@app.put("/api/me/language")
async def set_my_language(
    body: LanguageUpdate,
    user: TelegramUser = Depends(current_user),
) -> dict:
    """Переключатель RU/EN в Mini App пишет в тот же users.language, что и
    /language в боте, — язык бота и Mini App остаётся одинаковым."""
    await repo.set_user_language(user.id, body.language)
    return {"language": body.language}


@app.get("/api/refs")
async def refs(lang: str = "ru") -> dict:
    """Все справочники одним запросом — фронт кеширует на сессию."""
    return all_refs("en" if lang == "en" else "ru")


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
    # Новые анкеты сразу получают уже заполненную «Основную информацию».
    base = await repo.get_base_profile(user.id)
    filled = {k: base[k] for k in repo.BASE_FIELDS if base.get(k) not in (None, "")}
    if filled:
        await repo.set_base_profile(user.id, filled)
        subs = await repo.get_subscriptions(user.id)
    return {"subscriptions": subs}


@app.get("/api/base-profile")
async def get_base_profile_endpoint(user: TelegramUser = Depends(current_user)) -> dict:
    """«Основная информация» — общие поля всех анкет юзера."""
    return await repo.get_base_profile(user.id)


@app.put("/api/base-profile")
async def put_base_profile_endpoint(
    body: dict,
    user: TelegramUser = Depends(current_user),
) -> dict:
    """Сохранить общие поля сразу во все анкеты юзера."""
    from api.schemas import _BaseProfileSchema

    payload = {k: v for k, v in body.items() if k in repo.BASE_FIELDS}
    validated = _BaseProfileSchema.model_validate(payload)
    return await repo.set_base_profile(user.id, validated.model_dump(exclude_unset=True))


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
    current = await repo.get_category_profile(user.id, category)
    missing = repo.missing_required_fields(current, category)
    if missing:
        base_missing = [f for f in missing if f in repo.BASE_FIELDS]
        raise HTTPException(
            status_code=400,
            detail=(
                "Сначала заполни «Основную информацию»." if base_missing
                else "Заполни обязательные поля анкеты."
            ),
        )
    p, was_first_time = await repo.complete_category_profile(user.id, category)
    if p is None:
        raise HTTPException(status_code=400, detail="Profile not found")
    await _notify_user(user.id, _category_completion_text(category, was_first_time))
    return p


# ---------- Blacklist ----------


# ---------- Channel suggestion ----------


# ---------- Delivery settings ----------


@app.get("/api/delivery-settings", response_model=DeliverySettingsResponse)
async def get_delivery(user: TelegramUser = Depends(current_user)) -> DeliverySettingsResponse:
    import asyncio as _asyncio
    s, pending_count = await _asyncio.gather(
        repo.get_delivery_settings(user.id),
        repo.count_pending(user.id),
    )
    return DeliverySettingsResponse(**s, pending_count=pending_count)


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

    from bot import i18n
    from bot.handlers import _send_next_pending

    bot = Bot(
        settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        lang = await i18n.get_lang(user.id, user.language_code)
        sent = await _send_next_pending(bot, user.id, lang)
    finally:
        await bot.session.close()
    remaining = await repo.count_pending(user.id)
    return DigestStartResponse(sent=sent, remaining=remaining)


# ---------- Subscription / payments ----------


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


async def _build_favorite_message(
    user_id: int, message_id: int, matched_vacancy_ids: list[int],
) -> tuple[str, dict] | None:
    """Собрать (notification_text, reply_markup) для пере-отправки в чат
    из избранного. Возвращает None если canonical Message исчез."""
    from bot.keyboards import EMOJI_RESPOND, SHOW_RESPOND_BUTTONS
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
    for i in (matched_idxs if SHOW_RESPOND_BUTTONS else []):
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
        from bot import i18n

        lang = await i18n.get_lang(payment.user_id, None)
        until = new_until.strftime("%d.%m.%Y")
        text = i18n.t(
            lang,
            f"✅ <b>Подписка активна!</b>\n\nДействует до <b>{until}</b>. Спасибо!",
            f"✅ <b>Subscription active!</b>\n\nValid until <b>{until}</b>. Thank you!",
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
                        # Кнопка в главное меню бота (bot/menu.py: CB_MAIN).
                        "reply_markup": {"inline_keyboard": [[{
                            "text": i18n.t(lang, "🏠 В главное меню", "🏠 Main menu"),
                            "callback_data": "menu:main",
                        }]]},
                    },
                )
        except httpx.HTTPError as e:
            logger.warning("Subscription confirmation send failed: {}", e)
    return {"ok": True}
