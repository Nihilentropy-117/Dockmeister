from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Container:
    id: str
    name: str
    image: str
    status: str = "unknown"
    health: str | None = None
    cpu_percent: float = 0.0
    mem_usage: str = "0B"
    mem_usage_bytes: int = 0
    net_io: str = "0B/0B"
    ports: list[str] = field(default_factory=list)
    volumes: list[str] = field(default_factory=list)
    networks: list[str] = field(default_factory=list)


@dataclass
class ContainerStats:
    cpu_percent: float = 0.0
    mem_usage_bytes: int = 0
    mem_limit_bytes: int = 0
    net_rx_bytes: int = 0
    net_tx_bytes: int = 0
