from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

HELP_TEXT = """\
[bold]Dockmeister Keybindings[/bold]

[bold]Navigation[/bold]
  \u2191/\u2193 or j/k    Navigate stack list
  Enter        Select/expand stack
  Tab          Cycle panel focus
  1-9          Jump to container N

[bold]Lifecycle[/bold]
  u            docker compose up -d
  d            docker compose down
  r            docker compose restart
  p            docker compose pull
  R            Recreate (pull + down + up)

[bold]Global[/bold]
  U            Up all enabled stacks
  P            Pull all stacks
  D            Down all stacks (confirm)

[bold]Editing[/bold]
  e            Edit docker-compose.yml
  E            Edit .env file

[bold]Monitoring[/bold]
  l            Toggle log panel focus
  s            Shell into container

[bold]Management[/bold]
  f            Toggle favorite
  x            Enable/disable stack
  /            Fuzzy search
  h            Action history

[bold]System[/bold]
  t            Toggle green/amber theme
  Ctrl+P       Prune panel
  ?            This help
  q            Quit

[bold]Confirm Dialogs[/bold]
  Ctrl+D       Confirm destructive action
  Escape       Cancel
"""


class HelpOverlay(ModalScreen):
    DEFAULT_CSS = """
    HelpOverlay {
        align: center middle;
    }

    HelpOverlay > Vertical {
        width: 52;
        height: 80%;
        border: solid $secondary;
        background: $surface;
        padding: 1 2;
    }

    HelpOverlay Static {
        width: 100%;
    }

    HelpOverlay #help-title {
        text-style: bold;
        text-align: center;
        height: 1;
    }

    HelpOverlay #help-close {
        dock: bottom;
        height: 1;
        text-align: center;
        color: $secondary;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("question_mark", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Dockmeister Help", id="help-title")
            with VerticalScroll():
                yield Static(HELP_TEXT, id="help-content")
            yield Static("Press ? or Esc to close", id="help-close")

    def action_dismiss(self) -> None:
        self.dismiss()
