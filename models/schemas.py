"""Pydantic-схемы для извлечённых данных и пользовательских фильтров."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class VacancyExtraction(BaseModel):
    """Одна вакансия (роль) внутри поста."""

    role_types: list[str] = []
    gender: Optional[Literal["male", "female"]] = None
    age_min: Optional[int] = Field(None, ge=0, le=120)
    age_max: Optional[int] = Field(None, ge=0, le=120)
    rate: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    role_label: Optional[str] = None


class PostExtraction(BaseModel):
    """Структура, которую LLM извлекает из объявления о кастинге.

    Поля поста (project_types, city, summary, is_casting, confidence) —
    общие для всего объявления; vacancies — список ролей, у каждой свои
    условия (gender / age / rate / role_types).
    """

    is_casting: bool = False
    project_types: list[str] = []
    city: Optional[str] = None
    summary: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    vacancies: list[VacancyExtraction] = []


class UserFilter(BaseModel):
    """Устаревшая модель текстового фильтра. Сейчас матчинг идёт по
    actor_profiles (см. db.matching), но схема остаётся для совместимости
    с историческими данными в таблице filters.
    """

    user_id: int
    target_gender: Optional[Literal["male", "female"]] = None
    min_age: Optional[int] = Field(None, ge=0, le=120)
    max_age: Optional[int] = Field(None, ge=0, le=120)
    category: Optional[str] = None
    min_confidence: float = Field(0.5, ge=0.0, le=1.0)
