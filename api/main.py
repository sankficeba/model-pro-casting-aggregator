"""FastAPI-приложение для Mini App."""
from __future__ import annotations

import sys

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from api import profile_repo
from api.auth import TelegramUser, current_user
from api.reference_data import all_refs
from api.schemas import ProfileResponse, ProfileUpdate
from config import settings

COMPLETION_MESSAGE = (
    "✅ Анкета успешно заполнена. "
    "Теперь вам будут поступать подходящие кастинги."
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


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


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
    """Финальное завершение анкеты: уведомляем пользователя в боте."""
    p = await profile_repo.get_profile(user.id)
    if p is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Профиль не найден",
        )
    await _notify_user(user.id, COMPLETION_MESSAGE)
    return p
