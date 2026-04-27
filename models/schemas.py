"""Pydantic-схемы для извлечённых данных и пользовательских фильтров."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ExtractedData(BaseModel):
    """Структура, которую LLM извлекает из объявления."""

    gender: Optional[Literal["male", "female"]] = None
    age: Optional[int] = Field(None, ge=0, le=120)
    category: Optional[str] = None
    summary: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class UserFilter(BaseModel):
    """Фильтр конкретного пользователя aiogram-бота."""

    user_id: int
    target_gender: Optional[Literal["male", "female"]] = None
    min_age: Optional[int] = Field(None, ge=0, le=120)
    max_age: Optional[int] = Field(None, ge=0, le=120)
    category: Optional[str] = None  # подстрока поиска по category
    min_confidence: float = Field(0.5, ge=0.0, le=1.0)

    def matches(self, data: ExtractedData) -> bool:
        """Проверяет, подходит ли извлечённое объявление под фильтр."""
        if data.confidence < self.min_confidence:
            return False
        if self.target_gender and data.gender != self.target_gender:
            return False
        if self.min_age is not None and (data.age is None or data.age < self.min_age):
            return False
        if self.max_age is not None and (data.age is None or data.age > self.max_age):
            return False
        if self.category:
            if not data.category or self.category.lower() not in data.category.lower():
                return False
        return True
