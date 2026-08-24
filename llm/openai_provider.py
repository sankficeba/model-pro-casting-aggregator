"""LLM-провайдер на базе OpenAI-совместимого API."""
from __future__ import annotations

from openai import APIStatusError, AsyncOpenAI, RateLimitError

from llm.base import LLMBillingError, LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def _complete_json(self, system: str, user: str) -> str:
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
        except RateLimitError as e:
            raise LLMBillingError(str(e)) from e
        except APIStatusError as e:
            # DeepSeek (и другие OpenAI-совместимые провайдеры) отдают 402
            # Insufficient Balance вместо 429 — тоже billing-ошибка, должна
            # уйти в retry-очередь, а не потеряться как обычный сбой.
            if e.status_code == 402:
                raise LLMBillingError(str(e)) from e
            raise
        return resp.choices[0].message.content or "{}"
