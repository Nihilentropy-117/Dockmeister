from __future__ import annotations

from typing import Any, Generator

import docker
from docker.models.containers import Container as DockerContainer

from dockmeister.models.container import Container, ContainerStats


class DockerService:
    def __init__(self) -> None:
        self._client: docker.DockerClient | None = None

    def connect(self) -> None:
        self._client = docker.DockerClient.from_env()

    @property
    def client(self) -> docker.DockerClient:
        if self._client is None:
            self.connect()
        assert self._client is not None
        return self._client

    def list_containers(
        self, project: str | None = None, all: bool = True
    ) -> list[Container]:
        filters: dict[str, Any] = {}
        if project:
            filters["label"] = [f"com.docker.compose.project={project}"]
        try:
            raw = self.client.containers.list(all=all, filters=filters)
        except Exception:
            return []
        return [self._to_container(c) for c in raw]

    def _to_container(self, c: DockerContainer) -> Container:
        labels = c.labels or {}
        ports = []
        try:
            port_bindings = c.attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
            for container_port, bindings in port_bindings.items():
                if bindings:
                    for b in bindings:
                        ports.append(f"{b.get('HostPort', '?')}:{container_port}")
                else:
                    ports.append(container_port)
        except Exception:
            pass

        networks = []
        try:
            net_settings = c.attrs.get("NetworkSettings", {}).get("Networks", {}) or {}
            networks = list(net_settings.keys())
        except Exception:
            pass

        volumes = []
        try:
            mounts = c.attrs.get("Mounts", []) or []
            for m in mounts:
                volumes.append(m.get("Destination", m.get("Source", "?")))
        except Exception:
            pass

        health = None
        try:
            state = c.attrs.get("State", {})
            health_data = state.get("Health", {})
            if health_data:
                health = health_data.get("Status")
        except Exception:
            pass

        return Container(
            id=c.id or "",
            name=c.name or labels.get("com.docker.compose.service", ""),
            image=c.image.tags[0] if c.image and c.image.tags else str(c.image),
            status=c.status or "unknown",
            health=health,
            ports=ports,
            volumes=volumes,
            networks=networks,
        )

    def get_stats(self, container_id: str) -> ContainerStats:
        try:
            c = self.client.containers.get(container_id)
            stats = c.stats(stream=False)
            return self._parse_stats(stats)
        except Exception:
            return ContainerStats()

    def _parse_stats(self, stats: dict) -> ContainerStats:
        cpu = self._calc_cpu_percent(stats)
        mem = stats.get("memory_stats", {})
        mem_usage = mem.get("usage", 0)
        mem_limit = mem.get("limit", 0)

        net = stats.get("networks", {})
        rx = sum(v.get("rx_bytes", 0) for v in net.values())
        tx = sum(v.get("tx_bytes", 0) for v in net.values())

        return ContainerStats(
            cpu_percent=cpu,
            mem_usage_bytes=mem_usage,
            mem_limit_bytes=mem_limit,
            net_rx_bytes=rx,
            net_tx_bytes=tx,
        )

    def _calc_cpu_percent(self, stats: dict) -> float:
        cpu_stats = stats.get("cpu_stats", {})
        precpu_stats = stats.get("precpu_stats", {})
        cpu_delta = cpu_stats.get("cpu_usage", {}).get("total_usage", 0) - precpu_stats.get(
            "cpu_usage", {}
        ).get("total_usage", 0)
        system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get(
            "system_cpu_usage", 0
        )
        ncpus = cpu_stats.get("online_cpus", 1) or 1
        if system_delta > 0 and cpu_delta >= 0:
            return round((cpu_delta / system_delta) * ncpus * 100, 1)
        return 0.0

    def stream_logs(
        self, container_id: str, tail: int = 100
    ) -> Generator[bytes, None, None]:
        try:
            c = self.client.containers.get(container_id)
            return c.logs(stream=True, follow=True, tail=tail, timestamps=True)
        except Exception:
            return iter([])

    def exec_command(self, container_id: str, cmd: str) -> tuple[int, str]:
        try:
            c = self.client.containers.get(container_id)
            result = c.exec_run(cmd)
            return result.exit_code, result.output.decode("utf-8", errors="replace")
        except Exception as e:
            return 1, str(e)

    def get_image_digest(self, image_name: str) -> str | None:
        try:
            img = self.client.images.get(image_name)
            digests = img.attrs.get("RepoDigests", [])
            if digests:
                return digests[0].split("@")[-1]
        except Exception:
            pass
        return None

    def system_df(self) -> dict:
        try:
            return self.client.df()
        except Exception:
            return {}
