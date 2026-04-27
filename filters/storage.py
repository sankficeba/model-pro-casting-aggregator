"""JSON-хранилище пользовательских фильтров (для MVP — без БД)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Iterable

from loguru import logger

from models.schemas import ExtractedData, UserFilter


class FilterStorage:
    """Простое JSON-хранилище. Один пользователь — один фильтр (для MVP)."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        if not self.file_path.exists():
            self.file_path.write_text("{}", encoding="utf-8")

    async def _read(self) -> dict[str, dict]:
        async with self._lock:
            try:
                raw = self.file_path.read_text(encoding="utf-8") or "{}"
                return json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("filters.json повреждён — перезаписываю пустым словарём")
                return {}

    async def _write(self, data: dict[str, dict]) -> None:
        async with self._lock:
            self.file_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    async def upsert(self, f: UserFilter) -> None:
        data = await self._read()
        data[str(f.user_id)] = f.model_dump()
        await self._write(data)

    async def remove(self, user_id: int) -> bool:
        data = await self._read()
        removed = data.pop(str(user_id), None)
        if removed is not None:
            await self._write(data)
            return True
        return False

    async def get(self, user_id: int) -> UserFilter | None:
        data = await self._read()
        raw = data.get(str(user_id))
        return UserFilter(**raw) if raw else None

    async def all(self) -> list[UserFilter]:
        data = await self._read()
        return [UserFilter(**v) for v in data.values()]

    async def find_matches(self, extracted: ExtractedData) -> Iterable[UserFilter]:
        """Все фильтры, совпавшие с данными объявления."""
        return [f for f in await self.all() if f.matches(extracted)]
