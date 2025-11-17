from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import RichLog, Static


class LogViewer(Widget):
    DEFAULT_CSS = """
    LogViewer {
        height: 12;
    }
    """

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(" LOGS", id="log-header", classes="panel-title"),
            RichLog(id="log-output", max_lines=500, auto_scroll=True),
        )

    def write_log(self, line: str) -> None:
        self.query_one("#log-output", RichLog).write(line)

    def clear_logs(self) -> None:
        self.query_one("#log-output", RichLog).clear()

    def set_header(self, text: str) -> None:
        self.query_one("#log-header", Static).update(f" LOGS ({text})")
