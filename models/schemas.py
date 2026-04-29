"""Pydantic-схемы для извлечённых данных и пользовательских фильтров."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ExtractedData(BaseModel):
    """Структура, которую LLM извлекает из объявления о кастинге."""

    is_casting: bool = False
    gender: Optional[Literal["male", "female"]] = None
    # Возрастной диапазон, который ищут в кастинге.
    age_min: Optional[int] = Field(None, ge=0, le=120)
    age_max: Optional[int] = Field(None, ge=0, le=120)
    # Подмножество кодов из api/reference_data.py
    project_types: list[str] = []
    role_types: list[str] = []
    city: Optional[str] = None
    rate: Optional[int] = Field(None, ge=0)
    summary: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class UserFilter(BaseModel):
    """Устаревшая модель текстового фильтра. Сейчас матчинг идёт по
    actor_profiles (см. db.matching), но схема пока остаётся для
    совместимости с историческими данными в таблице filters.
    """

    user_id: int
    target_gender: Optional[Literal["male", "female"]] = None
    min_age: Optional[int] = Field(None, ge=0, le=120)
    max_age: Optional[int] = Field(None, ge=0, le=120)
    category: Optional[str] = None
    min_confidence: float = Field(0.5, ge=0.0, le=1.0)
