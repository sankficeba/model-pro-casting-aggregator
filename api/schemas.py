"""Pydantic-схемы для запросов/ответов FastAPI."""
from __future__ import annotations

from datetime import datetime
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
    experience_text: Optional[str] = Field(None, max_length=2000)
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


# Маппинг имени поля Pydantic → ключ справочника в all_codes() для случаев
# когда они отличаются. Если field_name не указан — используется как есть.
_FIELD_TO_REF_KEY = {
    "hair_color": "hair_colors",
    "hair_length": "hair_lengths",
    "eye_color": "eye_colors",
}


def _check_codes_array(v: list[str], ref_key: str) -> list[str]:
    """Все элементы должны быть из соответствующего справочника."""
    if not v:
        return v
    valid = _REF_CODES.get(ref_key, set())
    bad = [c for c in v if c not in valid]
    if bad:
        raise ValueError(f"Неизвестные коды для {ref_key}: {bad}")
    return v


def _check_single_code(v: Optional[str], ref_key: str) -> Optional[str]:
    """Скалярный код должен быть в справочнике."""
    if v is None or v == "":
        return None
    valid = _REF_CODES.get(ref_key, set())
    if v not in valid:
        raise ValueError(f"{ref_key}: код {v!r} не из справочника")
    return v


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

    @field_validator("tax_status", mode="after")
    @classmethod
    def _check_tax_status(cls, v: Optional[str]) -> Optional[str]:
        return _check_single_code(v, "tax_status")


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
    experience_text: Optional[str] = Field(default=None, max_length=2000)
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
    def _check_arrays(cls, v: list[str], info) -> list[str]:
        return _check_codes_array(v, info.field_name)

    @field_validator("hair_color", "hair_length", "education", "eye_color", mode="after")
    @classmethod
    def _check_singles(cls, v: Optional[str], info) -> Optional[str]:
        ref_key = _FIELD_TO_REF_KEY.get(info.field_name, info.field_name)
        return _check_single_code(v, ref_key)


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

    @field_validator("ethnicity", "body_type", mode="after")
    @classmethod
    def _check_arrays(cls, v: list[str], info) -> list[str]:
        return _check_codes_array(v, info.field_name)

    @field_validator("hair_color", "hair_length", mode="after")
    @classmethod
    def _check_singles(cls, v: Optional[str], info) -> Optional[str]:
        ref_key = _FIELD_TO_REF_KEY.get(info.field_name, info.field_name)
        return _check_single_code(v, ref_key)


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

    @field_validator("education", mode="after")
    @classmethod
    def _check_education(cls, v: Optional[str]) -> Optional[str]:
        return _check_single_code(v, "education")


# ---------- subscriptions ----------

CategoryCode = Literal["creative", "event", "general", "admin"]


class SubscriptionSchema(BaseModel):
    category: CategoryCode
    enabled: bool
    profile_completed: bool
    completion_pct: int = Field(0, ge=0, le=100)


class SubscriptionsCreateRequest(BaseModel):
    categories: list[CategoryCode]


class SubscriptionPatchRequest(BaseModel):
    enabled: bool


# ---------- suggestions ----------

class SuggestionsResponse(BaseModel):
    """Ответ /api/profile/suggestions: для каждого канонического ключа —
    список ранее введённых юзером значений (dedupe + sort by updated_at desc)."""

    suggestions: dict[str, list]


# ---------- blacklist ----------

class BlacklistResponse(BaseModel):
    """Список запрещённых слов/фраз юзера. При наличии любого в тексте
    поста уведомление не отправляется."""

    words: list[str]


class BlacklistUpdate(BaseModel):
    """PUT /api/blacklist body — полная замена списка."""

    words: list[str] = Field(default_factory=list, max_length=200)


# ---------- channel suggestion ----------

class ChannelSuggestionRequest(BaseModel):
    """POST /api/channel-suggestion body — юзер предлагает канал админу."""

    ref: str = Field(..., min_length=1, max_length=200)
    comment: Optional[str] = Field(default=None, max_length=500)


# ---------- delivery settings ----------

class DeliverySettingsResponse(BaseModel):
    delivery_mode: Literal["instant", "digest"]
    night_mode_enabled: bool
    night_start_hour: int = Field(..., ge=0, le=23)
    night_end_hour: int = Field(..., ge=0, le=23)
    digest_daily_enabled: bool
    digest_daily_hour: int = Field(..., ge=0, le=23)
    pending_count: int = 0


class DeliverySettingsUpdate(BaseModel):
    delivery_mode: Literal["instant", "digest"] = "instant"
    night_mode_enabled: bool = False
    night_start_hour: int = Field(default=23, ge=0, le=23)
    night_end_hour: int = Field(default=9, ge=0, le=23)
    digest_daily_enabled: bool = False
    digest_daily_hour: int = Field(default=20, ge=0, le=23)


class DigestStartResponse(BaseModel):
    sent: bool
    remaining: int


# ---------- subscription ----------


class FavoriteItem(BaseModel):
    """Элемент списка избранного для Mini App: компактная плашка с
    превью текста и метаинформацией. message_id — id канонического
    Message-row в БД, по нему фронт делает remove / show-in-chat."""
    message_id: int
    title: str  # короткий заголовок (категория + первая роль)
    preview: str  # 2-3 строки plain-text для карточки
    saved_at: datetime  # ISO timestamp
    source_label: str  # "@channel" / "приватный канал #N" / "источник"


class FavoritesListResponse(BaseModel):
    items: list[FavoriteItem]


class FavoriteShowResponse(BaseModel):
    sent: bool
    error: Optional[str] = None


class FavoritesSettings(BaseModel):
    retention_days: int = Field(5, ge=0, le=90)


class PerfEvent(BaseModel):
    """Клиентская метрика производительности из Mini App."""
    event: str = Field(..., max_length=64)
    total_ms: int = Field(..., ge=0, le=600_000)
    parts: dict[str, int] = Field(default_factory=dict)
    user_agent: Optional[str] = Field(None, max_length=256)


class ProblemReportRequest(BaseModel):
    text: str = Field(..., min_length=3, max_length=2000)


class ProblemItem(BaseModel):
    id: int
    user_id: int
    username: Optional[str] = None
    full_name: Optional[str] = None
    text: str
    created_at: datetime


class ProblemsListResponse(BaseModel):
    items: list[ProblemItem]


class ProblemActionResponse(BaseModel):
    ok: bool
    error: Optional[str] = None


class SubscriptionPlan(BaseModel):
    code: str
    days: int
    price_rub: int
    label: str
    discount_pct: int = 0
    badge: Optional[str] = None  # "Популярный" / "Выгодный" и т.д.


class SubscriptionStatusResponse(BaseModel):
    active_until: Optional[datetime] = None
    days_left: int = 0
    is_active: bool
    trial_started_at: Optional[datetime] = None
    plan_price_rub: int  # дефолтный (1m), оставляем для обратной совместимости
    plan_period_days: int
    payments_configured: bool
    plans: list[SubscriptionPlan]


class SubscriptionCheckoutRequest(BaseModel):
    plan_code: Optional[str] = None  # default: '1m'


class SubscriptionCheckoutResponse(BaseModel):
    confirmation_url: str
    payment_id: str
