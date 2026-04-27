"""Фабрика LLM-провайдеров — выбор по конфигу."""
from __future__ import annotations

from config import settings
from llm.base import LLMProvider
from llm.ollama_provider import OllamaProvider
from llm.openai_provider import OpenAIProvider


def get_llm_provider() -> LLMProvider:
    provider = settings.llm_provider.lower()

    if provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY не задан в .env")
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
        )

    if provider == "ollama":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )

    raise ValueError(f"Неизвестный LLM_PROVIDER: {settings.llm_provider}")
