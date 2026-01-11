from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, RichLog, Static


class LogViewer(Widget):
    DEFAULT_CSS = """
    LogViewer {
        height: 12;
    }
    """

    class SearchRequested(Message):
        pass

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(" LOGS", id="log-header", classes="panel-title"),
            RichLog(id="log-output", max_lines=500, auto_scroll=True),
            Input(placeholder="Search logs...", id="log-search"),
        )

    def on_mount(self) -> None:
        self.query_one("#log-search", Input).display = False

    def write_log(self, line: str) -> None:
        self.query_one("#log-output", RichLog).write(line)

    def clear_logs(self) -> None:
        self.query_one("#log-output", RichLog).clear()

    def set_header(self, text: str) -> None:
        self.query_one("#log-header", Static).update(f" LOGS ({text})")

    def show_search(self) -> None:
        search = self.query_one("#log-search", Input)
        search.display = True
        search.value = ""
        search.focus()

    def hide_search(self) -> None:
        search = self.query_one("#log-search", Input)
        search.display = False
        search.value = ""
