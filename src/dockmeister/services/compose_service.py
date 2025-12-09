from __future__ import annotations

from pathlib import Path

from python_on_whales import DockerClient

from dockmeister.services.discovery_service import COMPOSE_FILENAMES


class ComposeService:
    def __init__(self, stacks_dir: Path) -> None:
        self.stacks_dir = stacks_dir

    def _get_compose_file(self, stack_name: str) -> Path:
        stack_dir = self.stacks_dir / stack_name
        for name in COMPOSE_FILENAMES:
            path = stack_dir / name
            if path.exists():
                return path
        return stack_dir / "docker-compose.yml"

    def _get_client(self, stack_name: str) -> DockerClient:
        compose_file = self._get_compose_file(stack_name)
        return DockerClient(
            compose_files=[compose_file],
            compose_project_name=stack_name,
        )

    def ps(self, stack_name: str) -> list[dict]:
        client = self._get_client(stack_name)
        try:
            containers = client.compose.ps()
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "state": c.state.status if c.state else "unknown",
                }
                for c in containers
            ]
        except Exception:
            return []

    def up(self, stack_name: str) -> None:
        client = self._get_client(stack_name)
        client.compose.up(detach=True)

    def down(self, stack_name: str) -> None:
        client = self._get_client(stack_name)
        client.compose.down()

    def pull(self, stack_name: str) -> None:
        client = self._get_client(stack_name)
        client.compose.pull()

    def restart(self, stack_name: str) -> None:
        client = self._get_client(stack_name)
        client.compose.restart()

    def config(self, stack_name: str) -> str:
        client = self._get_client(stack_name)
        return str(client.compose.config())
