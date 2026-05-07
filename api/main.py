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
    CreativeProfileSchema,
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

FIRST_COMPLETION_MESSAGE = (
    "✅ Анкета успешно заполнена. "
    "Теперь вам будут поступать подходящие кастинги."
)
RECOMPLETION_MESSAGE = (
    "✏️ Анкета успешно изменена. Подборка кастингов обновлена."
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
    text = FIRST_COMPLETION_MESSAGE if was_first_time else RECOMPLETION_MESSAGE
    await _notify_user(user.id, text)
    return p
