"""Хранилище фильтров на PostgreSQL.

Сохраняем тот же интерфейс, что был у JSON-варианта, чтобы остальной код
(userbot, bot/handlers) не пришлось переписывать. По смыслу — это адаптер
поверх db/repository.py."""
from __future__ import annotations

from typing import Iterable

from db import repository
from models.schemas import ExtractedData, UserFilter


class FilterStorage:
    """Тонкая обёртка над репозиторием. Пока — один фильтр на пользователя."""

    def __init__(self, *_args, **_kwargs):
        # Аргументы оставлены для обратной совместимости с прежней инициализацией
        pass

    async def upsert(self, f: UserFilter) -> None:
        await repository.upsert_single_filter(f)

    async def remove(self, user_id: int) -> bool:
        deleted = await repository.remove_filters(user_id)
        return deleted > 0

    async def get(self, user_id: int) -> UserFilter | None:
        return await repository.get_user_filter(user_id)

    async def all(self) -> list[UserFilter]:
        return await repository.all_filters()

    async def find_matches(self, extracted: ExtractedData) -> Iterable[UserFilter]:
        return [f for f in await self.all() if f.matches(extracted)]
