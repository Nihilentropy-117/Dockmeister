from __future__ import annotations

from pathlib import Path

import aiosqlite

from dockmeister.models.stack import StackMeta


class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._init_schema()

    async def _init_schema(self) -> None:
        assert self._conn
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS stack_meta (
                name TEXT PRIMARY KEY,
                enabled INTEGER DEFAULT 1,
                favorite INTEGER DEFAULT 0,
                tags TEXT DEFAULT '[]',
                notes TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS action_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stack_name TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                details TEXT DEFAULT '',
                compose_snapshot TEXT
            );
            CREATE TABLE IF NOT EXISTS update_cache (
                image TEXT PRIMARY KEY,
                local_digest TEXT,
                remote_digest TEXT,
                checked_at TEXT
            );
        """)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def get_stack_meta(self, name: str) -> StackMeta | None:
        assert self._conn
        async with self._conn.execute(
            "SELECT name, enabled, favorite, tags, notes FROM stack_meta WHERE name = ?",
            (name,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return StackMeta(
                name=row["name"],
                enabled=bool(row["enabled"]),
                favorite=bool(row["favorite"]),
                tags=row["tags"],
                notes=row["notes"],
            )

    async def get_all_stack_meta(self) -> list[StackMeta]:
        assert self._conn
        async with self._conn.execute(
            "SELECT name, enabled, favorite, tags, notes FROM stack_meta"
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                StackMeta(
                    name=row["name"],
                    enabled=bool(row["enabled"]),
                    favorite=bool(row["favorite"]),
                    tags=row["tags"],
                    notes=row["notes"],
                )
                for row in rows
            ]

    async def upsert_stack_meta(self, meta: StackMeta) -> None:
        assert self._conn
        await self._conn.execute(
            """INSERT INTO stack_meta (name, enabled, favorite, tags, notes)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                   enabled = excluded.enabled,
                   favorite = excluded.favorite,
                   tags = excluded.tags,
                   notes = excluded.notes""",
            (meta.name, int(meta.enabled), int(meta.favorite), meta.tags, meta.notes),
        )
        await self._conn.commit()

    async def toggle_favorite(self, name: str) -> bool:
        assert self._conn
        await self._conn.execute(
            """INSERT INTO stack_meta (name, favorite) VALUES (?, 1)
               ON CONFLICT(name) DO UPDATE SET favorite = NOT favorite""",
            (name,),
        )
        await self._conn.commit()
        async with self._conn.execute(
            "SELECT favorite FROM stack_meta WHERE name = ?", (name,)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row["favorite"]) if row else False

    async def toggle_enabled(self, name: str) -> bool:
        assert self._conn
        await self._conn.execute(
            """INSERT INTO stack_meta (name, enabled) VALUES (?, 0)
               ON CONFLICT(name) DO UPDATE SET enabled = NOT enabled""",
            (name,),
        )
        await self._conn.commit()
        async with self._conn.execute(
            "SELECT enabled FROM stack_meta WHERE name = ?", (name,)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row["enabled"]) if row else True

    async def log_action(
        self,
        stack_name: str,
        action: str,
        details: str = "",
        compose_snapshot: str | None = None,
    ) -> None:
        assert self._conn
        from datetime import datetime, timezone

        await self._conn.execute(
            """INSERT INTO action_history (stack_name, action, timestamp, details, compose_snapshot)
               VALUES (?, ?, ?, ?, ?)""",
            (
                stack_name,
                action,
                datetime.now(timezone.utc).isoformat(),
                details,
                compose_snapshot,
            ),
        )
        await self._conn.commit()

    async def get_history(
        self, stack_name: str | None = None, limit: int = 50
    ) -> list[dict]:
        assert self._conn
        if stack_name:
            query = "SELECT * FROM action_history WHERE stack_name = ? ORDER BY id DESC LIMIT ?"
            params: tuple = (stack_name, limit)
        else:
            query = "SELECT * FROM action_history ORDER BY id DESC LIMIT ?"
            params = (limit,)
        async with self._conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_compose_snapshot(self, history_id: int) -> str | None:
        assert self._conn
        async with self._conn.execute(
            "SELECT compose_snapshot FROM action_history WHERE id = ?", (history_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["compose_snapshot"] if row else None
