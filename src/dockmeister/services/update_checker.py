from __future__ import annotations

from datetime import datetime, timezone

from dockmeister.db import Database
from dockmeister.services.docker_service import DockerService


class UpdateChecker:
    def __init__(self, docker_service: DockerService, db: Database) -> None:
        self._docker = docker_service
        self._db = db
        self._ttl_seconds = 3600  # 1 hour

    async def check_image(self, image: str) -> bool:
        # Check cache first
        assert self._db._conn
        async with self._db._conn.execute(
            "SELECT local_digest, remote_digest, checked_at FROM update_cache WHERE image = ?",
            (image,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                checked_at = datetime.fromisoformat(row["checked_at"])
                age = (datetime.now(timezone.utc) - checked_at).total_seconds()
                if age < self._ttl_seconds:
                    return row["local_digest"] != row["remote_digest"]

        # Get local digest
        local_digest = self._docker.get_image_digest(image)
        if not local_digest:
            return False

        # Get remote digest
        remote_digest = None
        try:
            reg_data = self._docker.client.images.get_registry_data(image)
            remote_digest = reg_data.attrs.get("Descriptor", {}).get("digest", "")
        except Exception:
            pass

        if not remote_digest:
            return False

        # Cache result
        now = datetime.now(timezone.utc).isoformat()
        await self._db._conn.execute(
            """INSERT INTO update_cache (image, local_digest, remote_digest, checked_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(image) DO UPDATE SET
                   local_digest = excluded.local_digest,
                   remote_digest = excluded.remote_digest,
                   checked_at = excluded.checked_at""",
            (image, local_digest, remote_digest, now),
        )
        await self._db._conn.commit()

        return local_digest != remote_digest

    async def check_stack_images(self, images: list[str]) -> dict[str, bool]:
        results: dict[str, bool] = {}
        for image in images:
            try:
                results[image] = await self.check_image(image)
            except Exception:
                results[image] = False
        return results
