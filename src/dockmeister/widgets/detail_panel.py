from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Static


class DetailPanel(Widget):
    DEFAULT_CSS = """
    DetailPanel {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(" Select a stack", id="detail-header", classes="panel-title"),
            Static("", id="detail-containers"),
            Static("", id="detail-info"),
            id="detail-content",
        )

    def show_stack(self, name: str) -> None:
        header = self.query_one("#detail-header", Static)
        header.update(f" {name}")
        containers = self.query_one("#detail-containers", Static)
        containers.update(
            " CONTAINERS         CPU   MEM    NET\n"
            " (no data yet)"
        )
        info = self.query_one("#detail-info", Static)
        info.update(
            " PORTS  —\n"
            " VOLS   —\n"
            " NETS   —"
        )
