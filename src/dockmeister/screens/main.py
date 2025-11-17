from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Static

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

    def on_stack_list_panel_stack_selected(
        self, message: StackListPanel.StackSelected
    ) -> None:
        self.query_one(DetailPanel).show_stack(message.stack_name)

    def action_toggle_theme(self) -> None:
        self.app.theme = "p3" if self.app.theme == "p1" else "p1"

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
        self.notify("Search: not implemented yet")

    def action_help(self) -> None:
        self.notify("Help: not implemented yet")

    def action_history(self) -> None:
        self.notify("History: not implemented yet")
