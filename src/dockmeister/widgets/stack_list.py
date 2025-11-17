from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, ListItem, ListView, Static


class StackListItem(ListItem):
    def __init__(self, name: str, favorite: bool = False, status: str = "unknown") -> None:
        super().__init__()
        self.stack_name = name
        self.favorite = favorite
        self.stack_status = status

    def compose(self) -> ComposeResult:
        star = "\u2605 " if self.favorite else "  "
        yield Label(f"{star}{self.stack_name}")


class StackListPanel(Widget):
    DEFAULT_CSS = """
    StackListPanel {
        width: 24;
        height: 100%;
    }
    """

    class StackSelected(Message):
        def __init__(self, stack_name: str) -> None:
            super().__init__()
            self.stack_name = stack_name

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(" STACKS", classes="panel-title"),
            ListView(
                StackListItem("plex", favorite=True),
                StackListItem("arr", favorite=True),
                StackListItem("nginx"),
                StackListItem("postgres"),
                StackListItem("redis"),
                id="stack-list",
            ),
            Static(" \\[/] Search", classes="panel-footer"),
        )

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item and isinstance(event.item, StackListItem):
            self.post_message(self.StackSelected(event.item.stack_name))
