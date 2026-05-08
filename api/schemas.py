"""Pydantic-схемы для запросов/ответов FastAPI."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator

from api.reference_data import all_codes


class ProfileBase(BaseModel):
    """Все поля анкеты. Все опциональные — анкету можно сохранять промежуточно."""

    # Step 1
    full_name: Optional[str] = Field(None, max_length=128)
    gender: Optional[Literal["male", "female"]] = None
    city: Optional[str] = Field(None, max_length=64)
    ready_for_travel: bool = False
    actual_age: Optional[int] = Field(None, ge=0, le=120)
    play_age_min: Optional[int] = Field(None, ge=0, le=120)
    play_age_max: Optional[int] = Field(None, ge=0, le=120)

    # Step 2
    project_types: list[str] = []
    role_types: list[str] = []
    min_rate: Optional[int] = Field(None, ge=0)
    show_negotiable: bool = False
    show_noncommercial: bool = True
    show_agency: bool = True

    # Step 3
    height_cm: Optional[int] = Field(None, ge=50, le=250)
    clothing_size: Optional[int] = Field(None, ge=20, le=80)
    shoe_size: Optional[int] = Field(None, ge=20, le=60)
    ethnicity: list[str] = []
    body_type: list[str] = []
    hair_color: Optional[str] = None
    hair_length: Optional[str] = None

    # Step 4
    has_experience: Optional[bool] = None
    education: Optional[str] = None
    tax_status: Optional[str] = None

    # Step 5
    eye_color: Optional[str] = None
    marks: list[str] = []
    skills_sport: list[str] = []
    skills_dance: list[str] = []
    skills_vocal: list[str] = []
    skills_instruments: list[str] = []

    # Step 6
    portfolio_url: Optional[str] = Field(None, max_length=500)
    video_url: Optional[str] = Field(None, max_length=500)
    professional_url: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=32)
    vk_url: Optional[str] = Field(None, max_length=500)
    email: Optional[EmailStr] = None

    @field_validator(
        "project_types",
        "role_types",
        "ethnicity",
        "body_type",
        "marks",
        "skills_sport",
        "skills_dance",
        "skills_vocal",
        "skills_instruments",
        mode="after",
    )
    @classmethod
    def _validate_array_codes(cls, v: list[str], info) -> list[str]:
        """Все элементы должны быть из соответствующего справочника."""
        if not v:
            return v
        codes = all_codes()
        valid = codes.get(info.field_name, set())
        bad = [c for c in v if c not in valid]
        if bad:
            raise ValueError(f"Неизвестные коды для {info.field_name}: {bad}")
        return v

    @field_validator("hair_color", "hair_length", "education", "tax_status", "eye_color", mode="after")
    @classmethod
    def _validate_single_code(cls, v: Optional[str], info) -> Optional[str]:
        if v is None or v == "":
            return None
        codes = all_codes()
        # имена полей могут отличаться от ключей справочника
        ref_key = {
            "hair_color": "hair_colors",
            "hair_length": "hair_lengths",
            "education": "education",
            "tax_status": "tax_status",
            "eye_color": "eye_colors",
        }[info.field_name]
        valid = codes.get(ref_key, set())
        if v not in valid:
            raise ValueError(f"{info.field_name}: код {v!r} не из справочника")
        return v


class ProfileResponse(ProfileBase):
    """То, что возвращает GET /api/profile (плюс мета)."""

    user_id: int
    completion_pct: int = Field(0, ge=0, le=100)


class ProfileUpdate(ProfileBase):
    """То, что принимает PUT /api/profile."""


# ====================================================================
# Per-category profile schemas (mini-app categories feature)
# ====================================================================
# Имена импортов BaseModel/EmailStr/Field/field_validator/Literal/Optional
# уже подняты выше — не дублируем.

_REF_CODES = all_codes()
_VALID_EVENT_WORK_TYPES = _REF_CODES["work_types_event"]
_VALID_GENERAL_WORK_TYPES = _REF_CODES["work_types_general"]
_VALID_ADMIN_WORK_TYPES = _REF_CODES["work_types_admin"]
_VALID_PHYSICAL_FITNESS = {"light", "medium", "heavy"}


class _BaseProfileSchema(BaseModel):
    """Общие поля всех 4 категорий — все Optional на этапе draft."""

    full_name: Optional[str] = Field(default=None, max_length=128)
    gender: Optional[Literal["male", "female"]] = None
    city: Optional[str] = Field(default=None, max_length=64)
    ready_for_travel: bool = False
    actual_age: Optional[int] = Field(default=None, ge=0, le=120)
    min_rate: Optional[int] = Field(default=None, ge=0)
    tax_status: Optional[str] = Field(default=None, max_length=32)
    phone: Optional[str] = Field(default=None, max_length=32)
    vk_url: Optional[str] = None
    telegram_user: Optional[str] = Field(default=None, max_length=64)
    email: Optional[EmailStr] = None


class CreativeProfileSchema(_BaseProfileSchema):
    play_age_min: Optional[int] = Field(default=None, ge=0, le=120)
    play_age_max: Optional[int] = Field(default=None, ge=0, le=120)
    project_types: list[str] = Field(default_factory=list)
    role_types: list[str] = Field(default_factory=list)
    show_negotiable: bool = False
    show_noncommercial: bool = True
    show_agency: bool = True
    height_cm: Optional[int] = Field(default=None, ge=100, le=250)
    clothing_size: Optional[int] = Field(default=None, ge=20, le=80)
    shoe_size: Optional[int] = Field(default=None, ge=30, le=55)
    ethnicity: list[str] = Field(default_factory=list)
    body_type: list[str] = Field(default_factory=list)
    hair_color: Optional[str] = Field(default=None, max_length=32)
    hair_length: Optional[str] = Field(default=None, max_length=32)
    has_experience: Optional[bool] = None
    education: Optional[str] = Field(default=None, max_length=32)
    eye_color: Optional[str] = Field(default=None, max_length=32)
    marks: list[str] = Field(default_factory=list)
    skills_sport: list[str] = Field(default_factory=list)
    skills_dance: list[str] = Field(default_factory=list)
    skills_vocal: list[str] = Field(default_factory=list)
    skills_instruments: list[str] = Field(default_factory=list)
    portfolio_url: Optional[str] = None
    video_url: Optional[str] = None
    professional_url: Optional[str] = None


class EventProfileSchema(_BaseProfileSchema):
    show_negotiable: bool = False
    show_noncommercial: bool = True
    height_cm: Optional[int] = Field(default=None, ge=100, le=250)
    clothing_size: Optional[int] = Field(default=None, ge=20, le=80)
    shoe_size: Optional[int] = Field(default=None, ge=30, le=55)
    ethnicity: list[str] = Field(default_factory=list)
    body_type: list[str] = Field(default_factory=list)
    hair_color: Optional[str] = Field(default=None, max_length=32)
    hair_length: Optional[str] = Field(default=None, max_length=32)
    work_types: list[str] = Field(default_factory=list)
    has_experience: Optional[bool] = None
    experience_text: Optional[str] = Field(default=None, max_length=2000)
    portfolio_url: Optional[str] = None
    video_url: Optional[str] = None

    @field_validator("work_types")
    @classmethod
    def _validate_work_types(cls, v: list[str]) -> list[str]:
        invalid = set(v) - _VALID_EVENT_WORK_TYPES
        if invalid:
            raise ValueError(f"Недопустимые work_types: {invalid}")
        return v


class GeneralProfileSchema(_BaseProfileSchema):
    height_cm: Optional[int] = Field(default=None, ge=100, le=250)
    physical_fitness: Optional[str] = Field(default=None, max_length=16)
    work_types: list[str] = Field(default_factory=list)
    has_experience: Optional[bool] = None
    experience_text: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("physical_fitness")
    @classmethod
    def _validate_physical_fitness(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _VALID_PHYSICAL_FITNESS:
            raise ValueError(f"physical_fitness must be one of {_VALID_PHYSICAL_FITNESS}")
        return v

    @field_validator("work_types")
    @classmethod
    def _validate_work_types(cls, v: list[str]) -> list[str]:
        invalid = set(v) - _VALID_GENERAL_WORK_TYPES
        if invalid:
            raise ValueError(f"Недопустимые work_types: {invalid}")
        return v


class AdminProfileSchema(_BaseProfileSchema):
    education: Optional[str] = Field(default=None, max_length=32)
    work_types: list[str] = Field(default_factory=list)
    has_experience: Optional[bool] = None
    experience_text: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("work_types")
    @classmethod
    def _validate_work_types(cls, v: list[str]) -> list[str]:
        invalid = set(v) - _VALID_ADMIN_WORK_TYPES
        if invalid:
            raise ValueError(f"Недопустимые work_types: {invalid}")
        return v


# ---------- subscriptions ----------

CategoryCode = Literal["creative", "event", "general", "admin"]


class SubscriptionSchema(BaseModel):
    category: CategoryCode
    enabled: bool
    profile_completed: bool


class SubscriptionsCreateRequest(BaseModel):
    categories: list[CategoryCode]


class SubscriptionPatchRequest(BaseModel):
    enabled: bool


# ---------- suggestions ----------

class SuggestionsResponse(BaseModel):
    """Ответ /api/profile/suggestions: для каждого канонического ключа —
    список ранее введённых юзером значений (dedupe + sort by updated_at desc)."""

    suggestions: dict[str, list]
