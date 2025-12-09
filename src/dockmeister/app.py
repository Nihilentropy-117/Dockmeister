from pathlib import Path

from textual.app import App

from dockmeister.db import Database
from dockmeister.screens.main import MainScreen
from dockmeister.services.compose_service import ComposeService
from dockmeister.services.discovery_service import DiscoveryService
from dockmeister.services.docker_service import DockerService
from dockmeister.theme import THEME_P1, THEME_P3


class DockmeisterApp(App):
    TITLE = "Dockmeister"
    CSS_PATH = "dockmeister.tcss"

    def __init__(self, stacks_dir: Path | None = None) -> None:
        super().__init__()
        self.stacks_dir = stacks_dir or Path("stacks")
        self.db = Database(Path("data/Dockmeister.db"))
        self.docker_service = DockerService()
        self.compose_service = ComposeService(self.stacks_dir)
        self._discovery: DiscoveryService | None = None
        self._main_screen: MainScreen | None = None

    async def on_mount(self) -> None:
        self.register_theme(THEME_P1)
        self.register_theme(THEME_P3)
        self.theme = "p1"
        await self.db.connect()
        self._main_screen = MainScreen()
        await self.push_screen(self._main_screen)

    def start_discovery(self, on_change: callable) -> DiscoveryService:
        self._discovery = DiscoveryService(self.stacks_dir, on_change)
        self._discovery.start_watching()
        return self._discovery

    async def on_unmount(self) -> None:
        if self._discovery:
            self._discovery.stop_watching()
        await self.db.close()
