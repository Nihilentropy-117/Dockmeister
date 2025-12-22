from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class ConfirmDialog(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmDialog {
        align: center middle;
    }

    ConfirmDialog > Vertical {
        width: 50;
        height: auto;
        max-height: 12;
        border: solid $secondary;
        background: $surface;
        padding: 1 2;
    }

    ConfirmDialog Label {
        width: 100%;
        text-align: center;
        margin-bottom: 1;
    }

    ConfirmDialog .button-row {
        width: 100%;
        height: 3;
        align-horizontal: center;
    }

    ConfirmDialog Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, message: str, destructive: bool = False) -> None:
        super().__init__()
        self._message = message
        self._destructive = destructive

    def compose(self) -> ComposeResult:
        confirm_label = "Ctrl+D to confirm" if self._destructive else "Enter to confirm"
        with Vertical():
            yield Label(self._message)
            yield Label(f"({confirm_label})", classes="hint")
            from textual.containers import Horizontal

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                if not self._destructive:
                    yield Button("Confirm", variant="warning", id="confirm-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(False)
        elif event.button.id == "confirm-btn":
            self.dismiss(True)

    def key_ctrl_d(self) -> None:
        if self._destructive:
            self.dismiss(True)

    def on_key(self, event) -> None:
        if event.key == "enter" and not self._destructive:
            self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
