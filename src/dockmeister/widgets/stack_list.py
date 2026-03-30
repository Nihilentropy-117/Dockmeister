from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label, ListItem, ListView, Static

from dockmeister.models.stack import Stack, StackStatus


STATUS_INDICATORS = {
    StackStatus.UP: "[green]\u25cf[/]",
    StackStatus.DOWN: "[red]\u25cf[/]",
    StackStatus.PARTIAL: "[yellow]\u25cf[/]",
    StackStatus.UNKNOWN: "[dim]\u25cf[/]",
}


class StackListItem(ListItem):
    def __init__(self, stack: Stack) -> None:
        super().__init__()
        self.stack = stack

    def compose(self) -> ComposeResult:
        star = "\u2605 " if self.stack.favorite else "  "
        indicator = STATUS_INDICATORS.get(self.stack.status, "[dim]\u25cf[/]")
        update_dot = " [#ffaa00]\u25cf[/]" if self.stack.has_update else ""
        disabled = " [dim](off)[/]" if not self.stack.enabled else ""
        yield Label(f"{star}{indicator} {self.stack.name}{update_dot}{disabled}")


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

    def __init__(self) -> None:
        super().__init__()
        self._all_stacks: list[Stack] = []
        self._search_active = False

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(" STACKS", classes="panel-title"),
            ListView(id="stack-list"),
            Input(placeholder="Search...", id="search-input"),
            Static(" \\[/] Search", classes="panel-footer"),
        )

    def on_mount(self) -> None:
        self.query_one("#search-input", Input).display = False

    def refresh_stacks(self, stacks: list[Stack]) -> None:
        self._all_stacks = stacks
        sorted_stacks = sorted(
            stacks,
            key=lambda s: (not s.favorite, s.name.lower()),
        )
        list_view = self.query_one("#stack-list", ListView)
        list_view.clear()
        for stack in sorted_stacks:
            list_view.append(StackListItem(stack))

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item and isinstance(event.item, StackListItem):
            self.post_message(self.StackSelected(event.item.stack.name))

    def get_selected_stack_name(self) -> str | None:
        list_view = self.query_one("#stack-list", ListView)
        if list_view.highlighted_child and isinstance(
            list_view.highlighted_child, StackListItem
        ):
            return list_view.highlighted_child.stack.name
        return None

    def show_search(self) -> None:
        self._search_active = True
        search = self.query_one("#search-input", Input)
        search.display = True
        search.value = ""
        search.focus()

    def hide_search(self) -> None:
        self._search_active = False
        search = self.query_one("#search-input", Input)
        search.display = False
        search.value = ""

    def on_input_changed(self, event: Input.Changed) -> None:
        if not self._search_active:
            return
        query = event.value.lower()
        if not query:
            self.refresh_stacks(self._all_stacks)
            return
        filtered = [s for s in self._all_stacks if query in s.name.lower()]
        list_view = self.query_one("#stack-list", ListView)
        list_view.clear()
        sorted_stacks = sorted(filtered, key=lambda s: (not s.favorite, s.name.lower()))
        for stack in sorted_stacks:
            list_view.append(StackListItem(stack))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.hide_search()
        self.query_one("#stack-list", ListView).focus()

    def on_key(self, event) -> None:
        if event.key == "escape" and self._search_active:
            self.hide_search()
            self.refresh_stacks(self._all_stacks)
            self.query_one("#stack-list", ListView).focus()
            event.prevent_default()
            event.stop()
