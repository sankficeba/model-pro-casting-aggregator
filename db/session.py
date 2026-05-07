"""Async-движок и фабрика сессий SQLAlchemy."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import settings

# SQLite (через aiosqlite) использует NullPool, который не принимает
# pool_size / max_overflow. В проде Postgres — там пулим.
_engine_kwargs: dict = {"echo": False}
if settings.db_dsn.startswith("sqlite"):
    pass  # NullPool, без kwargs пула
else:
    _engine_kwargs.update(pool_pre_ping=True, pool_size=5, max_overflow=5)

engine: AsyncEngine = create_async_engine(settings.db_dsn, **_engine_kwargs)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def dispose_engine() -> None:
    await engine.dispose()
