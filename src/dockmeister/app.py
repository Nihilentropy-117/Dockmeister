from pathlib import Path

from textual.app import App
from textual.widgets import Static

from dockmeister.db import Database


class DockmeisterApp(App):
    TITLE = "Dockmeister"
    CSS_PATH = "dockmeister.tcss"
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self) -> None:
        super().__init__()
        self.db = Database(Path("data/Dockmeister.db"))

    def compose(self):
        yield Static("Dockmeister v0.1 — Loading...", id="loading")

    async def on_mount(self) -> None:
        await self.db.connect()

    async def on_unmount(self) -> None:
        await self.db.close()
