"""Конфигурация приложения, загружаемая из переменных окружения / .env"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram Userbot
    tg_api_id: int = Field(..., alias="TG_API_ID")
    tg_api_hash: str = Field(..., alias="TG_API_HASH")
    tg_phone: str = Field(..., alias="TG_PHONE")
    tg_session_name: str = Field("userbot", alias="TG_SESSION_NAME")

    # Каналы храним как строку — pydantic-settings не пытается JSON-декодировать,
    # а доступ идёт через свойство tg_channels (см. ниже).
    tg_channels_raw: str = Field("", alias="TG_CHANNELS")

    # Telegram Bot (aiogram)
    bot_token: str = Field(..., alias="BOT_TOKEN")

    # LLM
    llm_provider: str = Field("openai", alias="LLM_PROVIDER")
    openai_api_key: str | None = Field(None, alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o-mini", alias="OPENAI_MODEL")
    openai_base_url: str = Field("https://api.openai.com/v1", alias="OPENAI_BASE_URL")

    ollama_base_url: str = Field("http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field("llama3.1", alias="OLLAMA_MODEL")

    # Прочее
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    filters_file: str = Field("data/filters.json", alias="FILTERS_FILE")

    @property
    def tg_channels(self) -> list[str]:
        """CSV в .env -> список. Пустое значение -> пустой список."""
        if not self.tg_channels_raw:
            return []
        return [c.strip() for c in self.tg_channels_raw.split(",") if c.strip()]


settings = Settings()  # type: ignore[call-arg]
