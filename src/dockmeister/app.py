from pathlib import Path
from typing import Callable

from textual.app import App
from textual.binding import Binding

from dockmeister.db import Database
from dockmeister.screens.main import MainScreen
from dockmeister.services.compose_service import ComposeService
from dockmeister.services.discovery_service import DiscoveryService
from dockmeister.services.docker_service import DockerService
from dockmeister.services.stats_service import StatsService
from dockmeister.theme import THEME_P1, THEME_P3


class DockmeisterApp(App):
    TITLE = "Dockmeister"
    CSS_PATH = "dockmeister.tcss"

    BINDINGS = [
        Binding("tab", "focus_next", "Next Panel", show=False),
        Binding("shift+tab", "focus_previous", "Prev Panel", show=False),
    ]

    def __init__(self, stacks_dir: Path | None = None) -> None:
        super().__init__()
        self.stacks_dir = stacks_dir or Path("stacks")
        self.stacks_dir.mkdir(parents=True, exist_ok=True)
        Path("data").mkdir(parents=True, exist_ok=True)
        self.db = Database(Path("data/Dockmeister.db"))
        self.docker_service = DockerService()
        self.compose_service = ComposeService(self.stacks_dir)
        self.stats_service = StatsService(self.docker_service)
        self._discovery: DiscoveryService | None = None
        self._main_screen: MainScreen | None = None
        self._docker_available = True

    async def on_mount(self) -> None:
        self.register_theme(THEME_P1)
        self.register_theme(THEME_P3)
        self.theme = "p1"
        await self.db.connect()

        # Check Docker connectivity
        try:
            self.docker_service.connect()
        except Exception:
            self._docker_available = False

        self._main_screen = MainScreen()
        await self.push_screen(self._main_screen)

    def start_discovery(self, on_change: Callable[[], None]) -> DiscoveryService:
        self._discovery = DiscoveryService(self.stacks_dir, on_change)
        self._discovery.start_watching()
        return self._discovery

    async def on_unmount(self) -> None:
        if self._discovery:
            self._discovery.stop_watching()
        await self.db.close()
