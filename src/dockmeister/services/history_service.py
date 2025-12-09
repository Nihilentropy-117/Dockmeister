from __future__ import annotations

from dockmeister.db import Database


class HistoryService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def log_action(
        self,
        stack_name: str,
        action: str,
        details: str = "",
        compose_snapshot: str | None = None,
    ) -> None:
        await self.db.log_action(stack_name, action, details, compose_snapshot)

    async def get_history(
        self, stack_name: str | None = None, limit: int = 50
    ) -> list[dict]:
        return await self.db.get_history(stack_name, limit)

    async def get_compose_snapshot(self, history_id: int) -> str | None:
        return await self.db.get_compose_snapshot(history_id)
