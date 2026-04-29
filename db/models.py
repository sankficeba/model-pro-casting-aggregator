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
    gender: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint("tg_chat_id", "tg_message_id", name="uq_messages_chat_msg"),
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
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        # Дедуп: один пользователь не получает одно и то же сообщение дважды
        UniqueConstraint("user_id", "message_id", name="uq_notifications_user_msg"),
    )
