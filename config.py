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

    # PostgreSQL
    # Можно задать одной строкой DATABASE_URL ИЛИ пятью POSTGRES_* — они склеятся.
    database_url: str | None = Field(None, alias="DATABASE_URL")
    postgres_host: str = Field("postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(5432, alias="POSTGRES_PORT")
    postgres_db: str = Field("tg_parser", alias="POSTGRES_DB")
    postgres_user: str = Field("tg_parser", alias="POSTGRES_USER")
    postgres_password: str = Field("tg_parser", alias="POSTGRES_PASSWORD")

    # Прочее
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    @property
    def tg_channels(self) -> list[str]:
        if not self.tg_channels_raw:
            return []
        return [c.strip() for c in self.tg_channels_raw.split(",") if c.strip()]

    @property
    def db_dsn(self) -> str:
        """Async DSN для SQLAlchemy + asyncpg."""
        if self.database_url:
            # Если задано напрямую, ничего не меняем (но просим asyncpg-драйвер)
            if self.database_url.startswith("postgresql://"):
                return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def db_dsn_sync(self) -> str:
        """Sync DSN для Alembic (использует psycopg2-style URL без +asyncpg)."""
        return self.db_dsn.replace("+asyncpg", "")


settings = Settings()  # type: ignore[call-arg]
