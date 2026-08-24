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

    # Сообщения старше этого возраста при LLM-ретрае отбрасываются без
    # вызова LLM и без уведомлений — кастинг уже неактуален.
    llm_retry_max_age_hours: int = Field(48, alias="LLM_RETRY_MAX_AGE_HOURS")

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
    admin_ids_raw: str = Field("", alias="ADMIN_IDS")

    # Платная подписка
    subscription_trial_days: int = Field(7, alias="SUBSCRIPTION_TRIAL_DAYS")
    subscription_period_days: int = Field(30, alias="SUBSCRIPTION_PERIOD_DAYS")
    subscription_price_rub: int = Field(499, alias="SUBSCRIPTION_PRICE_RUB")
    subscription_return_url: str = Field("", alias="SUBSCRIPTION_RETURN_URL")

    # YooKassa
    yookassa_shop_id: str = Field("", alias="YOOKASSA_SHOP_ID")
    yookassa_secret_key: str = Field("", alias="YOOKASSA_SECRET_KEY")
    # Доп. shared-secret в URL вебхука для отсева левых запросов до парсинга.
    yookassa_webhook_token: str = Field("", alias="YOOKASSA_WEBHOOK_TOKEN")

    @property
    def tg_channels(self) -> list[str]:
        if not self.tg_channels_raw:
            return []
        return [c.strip() for c in self.tg_channels_raw.split(",") if c.strip()]

    @property
    def admin_ids(self) -> set[int]:
        """Set telegram user_id'ов, которым разрешены админ-команды бота."""
        if not self.admin_ids_raw:
            return set()
        out: set[int] = set()
        for x in self.admin_ids_raw.split(","):
            x = x.strip()
            if x.isdigit():
                out.add(int(x))
        return out

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
