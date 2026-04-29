"""Async-движок и фабрика сессий SQLAlchemy."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import settings

_engine_kwargs = {
    "echo": False,
}

# SQLite doesn't support pool_size/max_overflow; only PostgreSQL does
if not settings.db_dsn.startswith("sqlite"):
    _engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 5,
    })

engine: AsyncEngine = create_async_engine(settings.db_dsn, **_engine_kwargs)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def dispose_engine() -> None:
    await engine.dispose()
