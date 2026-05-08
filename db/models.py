"""SQLAlchemy 2.0 declarative модели."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    """Пользователь aiogram-бота. id = telegram user_id."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_active: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    filters: Mapped[list["Filter"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    profile: Mapped[Optional["ActorProfile"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class ActorProfile(Base):
    """Анкета актёра — заполняется через Mini App, один профиль на пользователя."""

    __tablename__ = "actor_profiles"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    # --- Step 1: Основная информация ---
    full_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)  # male/female
    city: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ready_for_travel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    actual_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    play_age_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    play_age_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # --- Step 2: Какие кастинги подходят ---
    project_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    role_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    min_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    show_negotiable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_noncommercial: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_agency: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # --- Step 3: Параметры для подбора ---
    height_cm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    clothing_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shoe_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ethnicity: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    body_type: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    hair_color: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    hair_length: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # --- Step 4: Профессиональные параметры ---
    has_experience: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    education: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    tax_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # --- Step 5: Дополнительные данные ---
    eye_color: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    marks: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    skills_sport: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    skills_dance: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    skills_vocal: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    skills_instruments: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )

    # --- Step 6: Материалы и контакты ---
    portfolio_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    professional_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    vk_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="profile")


class UserCategorySubscription(Base):
    """Подписка пользователя на категорию. Multi-row, по одной строке на
    категорию. enabled=False = категория временно выключена в settings, но
    данные профиля сохранены."""

    __tablename__ = "user_category_subscription"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_user_category"),
    )


class CreativeProfile(Base):
    """Анкета для категории «Творческие позиции» (актёры, модели).
    Поля идентичны старой ActorProfile + telegram_user."""

    __tablename__ = "creative_profile"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ready_for_travel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    actual_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    play_age_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    play_age_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    project_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    role_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    min_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    show_negotiable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_noncommercial: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_agency: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    height_cm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    clothing_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shoe_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ethnicity: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    body_type: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    hair_color: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    hair_length: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    has_experience: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    education: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    tax_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    eye_color: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    marks: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    skills_sport: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    skills_dance: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    skills_vocal: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    skills_instruments: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    portfolio_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    professional_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    vk_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    telegram_user: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class EventProfile(Base):
    """Анкета для категории «Event-персонал» (хостес, промо-модели, аниматоры)."""

    __tablename__ = "event_profile"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ready_for_travel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    actual_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    show_negotiable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_noncommercial: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    height_cm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    clothing_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shoe_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ethnicity: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    body_type: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    hair_color: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    hair_length: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    work_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    has_experience: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    experience_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tax_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    portfolio_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    vk_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    telegram_user: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class GeneralProfile(Base):
    """Анкета для категории «Разнорабочие» (хелперы, клининг, грузчики)."""

    __tablename__ = "general_profile"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ready_for_travel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    actual_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height_cm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    physical_fitness: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    work_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    has_experience: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    experience_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tax_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    vk_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    telegram_user: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AdminProfile(Base):
    """Анкета для категории «Администрирование» (операторы регистрации, супервайзеры)."""

    __tablename__ = "admin_profile"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ready_for_travel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    actual_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    education: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    work_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    has_experience: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    experience_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tax_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    vk_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    telegram_user: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Channel(Base):
    """Telegram-канал, который слушает userbot. Управляется из бота
    командами /addchannel / /removechannel.

    Поддерживаются два способа адресации:
    - Публичный канал по username (`@my_channel`).
    - Приватный канал по числовому id (`https://t.me/c/<id>`) — заполняется
      tg_chat_id (полная форма с -100, например -1001968214811). В этом
      случае username NULL. JoinChannelRequest пропускаем — на приватные
      каналы можно попасть только по invite-ссылке руками.
    Хотя бы одно из (username, tg_chat_id) должно быть задано.
    """

    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    tg_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, unique=True)
    added_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Filter(Base):
    """Один фильтр пользователя. У пользователя может быть несколько фильтров."""

    __tablename__ = "filters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_gender: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    min_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    min_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="filters")


class Message(Base):
    """История сообщений из каналов с извлечёнными LLM полями."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tg_chat_username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tg_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Дедуп форварднутых копий. text_hash — SHA-1 от нормализованного
    # текста (db/dedup.py). canonical_message_id указывает на первый
    # row с тем же хэшем; у canonical = NULL.
    text_hash: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    canonical_message_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Извлечённые LLM поля (текущая схема).
    is_casting: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    age_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    age_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    project_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    role_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    city: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Хвост от старой схемы — заполняется только в исторических строках,
    # новые записи их не используют. Оставлено для совместимости.
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    legacy_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Per-category matching: доминирующая категория поста, определённая LLM.
    category: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    vacancies: Mapped[list["Vacancy"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="Vacancy.idx",
    )

    __table_args__ = (
        UniqueConstraint("tg_chat_id", "tg_message_id", name="uq_messages_chat_msg"),
    )


class Vacancy(Base):
    """Одна вакансия (роль) внутри объявления о кастинге.
    Один Message → 0..N Vacancy."""

    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Порядок вакансии в посте (0,1,2...): даёт стабильный UX и
    # защищает от дубля при ретрае LLM-extract'а.
    idx: Mapped[int] = mapped_column(Integer, nullable=False)
    role_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False,
    )
    gender: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    age_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    age_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ethnicity: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False,
    )
    height_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    body_type: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False,
    )
    hair_color: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False,
    )
    hair_length: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role_label: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Per-category matching: override для гибрид-постов (если категория этой
    # вакансии отличается от доминирующей категории поста). NULL = inherit.
    category: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    # Коды work_types для event/general/admin вакансий (для creative — пусто).
    work_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )

    message: Mapped["Message"] = relationship(back_populates="vacancies")

    __table_args__ = (
        UniqueConstraint("message_id", "idx", name="uq_vacancies_message_idx"),
    )


class Notification(Base):
    """Лог уведомлений: какому пользователю по какому фильтру и какому сообщению ушло."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    # Хвост от старой модели; сейчас всегда NULL (матч идёт по actor_profiles).
    filter_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Денормализация text_hash из связанного Message: позволяет UNIQUE-дедуп
    # «один text_hash → одно уведомление на юзера» без JOIN на горячем пути.
    text_hash: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    matched_vacancy_ids: Mapped[Optional[list[int]]] = mapped_column(
        ARRAY(Integer), nullable=True,
    )

    __table_args__ = (
        # Дедуп: один пользователь не получает одно и то же сообщение дважды
        UniqueConstraint("user_id", "message_id", name="uq_notifications_user_msg"),
    )
