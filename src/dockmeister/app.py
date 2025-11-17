from pathlib import Path

from textual.app import App

from dockmeister.db import Database
from dockmeister.screens.main import MainScreen
from dockmeister.theme import THEME_P1, THEME_P3


class DockmeisterApp(App):
    TITLE = "Dockmeister"
    CSS_PATH = "dockmeister.tcss"

    def __init__(self) -> None:
        super().__init__()
        self.db = Database(Path("data/Dockmeister.db"))

    async def on_mount(self) -> None:
        self.register_theme(THEME_P1)
        self.register_theme(THEME_P3)
        self.theme = "p1"
        await self.db.connect()
        await self.push_screen(MainScreen())

    async def on_unmount(self) -> None:
        await self.db.close()
