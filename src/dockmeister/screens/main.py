from __future__ import annotations

import json
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Static
from textual import work
from textual.worker import get_current_worker, Worker

from dockmeister.models.container import Container
from dockmeister.models.stack import Stack, StackMeta, StackStatus
from dockmeister.widgets.detail_panel import DetailPanel
from dockmeister.widgets.log_viewer import LogViewer
from dockmeister.widgets.stack_list import StackListPanel


class MainScreen(Screen):
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("t", "toggle_theme", "Theme"),
        Binding("u", "stack_up", "Up"),
        Binding("d", "stack_down", "Down"),
        Binding("r", "stack_restart", "Restart"),
        Binding("p", "stack_pull", "Pull"),
        Binding("R", "stack_recreate", "Recreate", key_display="R"),
        Binding("U", "up_all", "Up All", key_display="U"),
        Binding("P", "pull_all", "Pull All", key_display="P"),
        Binding("D", "down_all", "Down All", key_display="D"),
        Binding("e", "edit_compose", "Edit"),
        Binding("E", "edit_env", "Edit .env", key_display="E"),
        Binding("l", "toggle_logs", "Logs"),
        Binding("s", "shell", "Shell"),
        Binding("f", "toggle_favorite", "Fav"),
        Binding("x", "toggle_enabled", "En/Dis"),
        Binding("slash", "search", "Search", key_display="/"),
        Binding("question_mark", "help", "Help", key_display="?"),
        Binding("h", "history", "History"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._stacks: list[Stack] = []
        self._selected_stack: Stack | None = None

    def compose(self) -> ComposeResult:
        yield Static(
            " Dockmeister v0.1              \u25b8 0 stacks \u2502 0 running",
            id="header-bar",
        )
        with Horizontal(id="main-container"):
            yield StackListPanel()
            with Vertical(id="right-container"):
                yield DetailPanel()
                yield LogViewer()
        yield Footer()

    def on_mount(self) -> None:
        self.app.start_discovery(on_change=self._on_fs_change)
        self._load_stacks()

    def _on_fs_change(self) -> None:
        self.app.call_from_thread(self._load_stacks)

    @work(thread=True, exclusive=True, group="scan")
    def _load_stacks(self) -> None:
        worker = get_current_worker()
        discovery = self.app._discovery
        if not discovery:
            return

        stack_names = discovery.scan()
        stacks: list[Stack] = []

        for name in stack_names:
            if worker.is_cancelled:
                return
            stack_path = self.app.stacks_dir / name
            stack = Stack(name=name, path=stack_path)

            # Get container info from Docker
            containers = self.app.docker_service.list_containers(project=name)
            stack.containers = containers

            # Determine status
            if not containers:
                stack.status = StackStatus.DOWN
            elif all(c.status == "running" for c in containers):
                stack.status = StackStatus.UP
            elif any(c.status == "running" for c in containers):
                stack.status = StackStatus.PARTIAL
            else:
                stack.status = StackStatus.DOWN

            stacks.append(stack)

        if worker.is_cancelled:
            return

        # Apply DB metadata (favorites, enabled state)
        self.app.call_from_thread(self._apply_metadata_and_refresh, stacks)

    def _apply_metadata_and_refresh(self, stacks: list[Stack]) -> None:
        self.run_worker(self._apply_metadata(stacks), exclusive=True, group="metadata")

    async def _apply_metadata(self, stacks: list[Stack]) -> None:
        all_meta = await self.app.db.get_all_stack_meta()
        meta_map = {m.name: m for m in all_meta}

        for stack in stacks:
            if stack.name in meta_map:
                meta = meta_map[stack.name]
                stack.favorite = meta.favorite
                stack.enabled = meta.enabled
                stack.tags = json.loads(meta.tags) if meta.tags else []
                stack.notes = meta.notes

        self._stacks = stacks
        self._update_header()
        self.query_one(StackListPanel).refresh_stacks(stacks)

        # Re-select previously selected stack if it still exists
        if self._selected_stack:
            for s in stacks:
                if s.name == self._selected_stack.name:
                    self._selected_stack = s
                    self.query_one(DetailPanel).show_stack(s)
                    break

    def _update_header(self) -> None:
        total = len(self._stacks)
        running = sum(
            len([c for c in s.containers if c.status == "running"])
            for s in self._stacks
        )
        header = self.query_one("#header-bar", Static)
        header.update(
            f" Dockmeister v0.1              \u25b8 {total} stacks \u2502 {running} running"
        )

    def on_stack_list_panel_stack_selected(
        self, message: StackListPanel.StackSelected
    ) -> None:
        for s in self._stacks:
            if s.name == message.stack_name:
                self._selected_stack = s
                self.query_one(DetailPanel).show_stack(s)
                break

    def _get_selected_name(self) -> str | None:
        return self._selected_stack.name if self._selected_stack else None

    # --- Theme ---

    def action_toggle_theme(self) -> None:
        self.app.theme = "p3" if self.app.theme == "p1" else "p1"

    # --- Stubs for later phases ---

    def action_stack_up(self) -> None:
        self.notify("Up: not implemented yet")

    def action_stack_down(self) -> None:
        self.notify("Down: not implemented yet")

    def action_stack_restart(self) -> None:
        self.notify("Restart: not implemented yet")

    def action_stack_pull(self) -> None:
        self.notify("Pull: not implemented yet")

    def action_stack_recreate(self) -> None:
        self.notify("Recreate: not implemented yet")

    def action_up_all(self) -> None:
        self.notify("Up all: not implemented yet")

    def action_pull_all(self) -> None:
        self.notify("Pull all: not implemented yet")

    def action_down_all(self) -> None:
        self.notify("Down all: not implemented yet")

    def action_edit_compose(self) -> None:
        self.notify("Editor: not implemented yet")

    def action_edit_env(self) -> None:
        self.notify("Env editor: not implemented yet")

    def action_toggle_logs(self) -> None:
        self.notify("Logs: not implemented yet")

    def action_shell(self) -> None:
        self.notify("Shell: not implemented yet")

    def action_toggle_favorite(self) -> None:
        self.notify("Favorite: not implemented yet")

    def action_toggle_enabled(self) -> None:
        self.notify("Enable/disable: not implemented yet")

    def action_search(self) -> None:
        self.query_one(StackListPanel).show_search()

    def action_help(self) -> None:
        self.notify("Help: not implemented yet")

    def action_history(self) -> None:
        self.notify("History: not implemented yet")
