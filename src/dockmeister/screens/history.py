from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static


class HistoryScreen(ModalScreen):
    DEFAULT_CSS = """
    HistoryScreen {
        align: center middle;
    }

    HistoryScreen > Vertical {
        width: 70;
        height: 80%;
        border: solid $secondary;
        background: $surface;
        padding: 1 2;
    }

    HistoryScreen #history-title {
        text-style: bold;
        text-align: center;
        height: 1;
        margin-bottom: 1;
    }

    HistoryScreen ListView {
        height: 1fr;
        background: $background;
    }

    HistoryScreen #history-footer {
        dock: bottom;
        height: 1;
        text-align: center;
        color: $secondary;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Close"),
        Binding("r", "rollback", "Rollback"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._history: list[dict] = []

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Action History", id="history-title")
            yield ListView(id="history-list")
            yield Static(
                "\\[r] Rollback compose  |  Esc close", id="history-footer"
            )

    def on_mount(self) -> None:
        self.run_worker(self._load_history())

    async def _load_history(self) -> None:
        self._history = await self.app.db.get_history(limit=100)
        list_view = self.query_one("#history-list", ListView)
        list_view.clear()
        for entry in self._history:
            ts = entry.get("timestamp", "")[:19]
            stack = entry.get("stack_name", "?")
            action = entry.get("action", "?")
            has_snapshot = "\u25cf" if entry.get("compose_snapshot") else " "
            label_text = f" {has_snapshot}  {ts}  {stack:<20} {action}"
            list_view.append(ListItem(Label(label_text)))

    def action_rollback(self) -> None:
        list_view = self.query_one("#history-list", ListView)
        if list_view.index is None or list_view.index >= len(self._history):
            return
        entry = self._history[list_view.index]
        snapshot = entry.get("compose_snapshot")
        if not snapshot:
            self.notify("No compose snapshot for this entry", severity="warning")
            return

        stack_name = entry.get("stack_name", "")
        from dockmeister.screens.confirm import ConfirmDialog

        def on_confirm(result: bool) -> None:
            if result:
                self.run_worker(self._do_rollback(stack_name, snapshot))

        self.app.push_screen(
            ConfirmDialog(
                f"Rollback {stack_name} to snapshot from {entry.get('timestamp', '?')[:19]}?"
            ),
            on_confirm,
        )

    async def _do_rollback(self, stack_name: str, snapshot: str) -> None:
        stacks_dir = self.app.stacks_dir
        compose_path = stacks_dir / stack_name / "docker-compose.yml"
        if compose_path.exists():
            # Backup current
            from datetime import datetime, timezone

            backup_dir = Path("data/backups") / stack_name
            backup_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
            (backup_dir / f"{ts}.yml").write_text(compose_path.read_text())

        compose_path.write_text(snapshot)
        await self.app.db.log_action(stack_name, "rollback")
        self.notify(f"Rolled back {stack_name}")
        self.dismiss()

    def action_cancel(self) -> None:
        self.dismiss()
