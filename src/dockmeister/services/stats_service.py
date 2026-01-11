from __future__ import annotations

from dockmeister.models.container import ContainerStats
from dockmeister.services.docker_service import DockerService


class StatsService:
    def __init__(self, docker_service: DockerService) -> None:
        self._docker = docker_service

    def get_stats(self, container_ids: list[str]) -> dict[str, ContainerStats]:
        results: dict[str, ContainerStats] = {}
        for cid in container_ids:
            results[cid] = self._docker.get_stats(cid)
        return results
