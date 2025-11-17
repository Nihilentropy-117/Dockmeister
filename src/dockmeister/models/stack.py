from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from dockmeister.models.container import Container


class StackStatus(Enum):
    UP = "up"
    DOWN = "down"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


@dataclass
class Stack:
    name: str
    path: Path
    enabled: bool = True
    favorite: bool = False
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    status: StackStatus = StackStatus.UNKNOWN
    containers: list[Container] = field(default_factory=list)
    has_update: bool = False

    @property
    def compose_file(self) -> Path:
        for name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
            p = self.path / name
            if p.exists():
                return p
        return self.path / "docker-compose.yml"

    @property
    def env_file(self) -> Path:
        return self.path / ".env"

    @property
    def running_count(self) -> int:
        return sum(1 for c in self.containers if c.status == "running")

    @property
    def healthy_count(self) -> int:
        return sum(1 for c in self.containers if c.health == "healthy")


@dataclass
class StackMeta:
    name: str
    enabled: bool = True
    favorite: bool = False
    tags: str = "[]"
    notes: str = ""
