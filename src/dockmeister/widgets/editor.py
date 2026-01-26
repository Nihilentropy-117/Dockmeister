from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static, TextArea


class EditorPanel(Screen):
    DEFAULT_CSS = """
    EditorPanel {
        background: $background;
    }

    EditorPanel #editor-header {
        dock: top;
        height: 1;
        background: $surface;
        color: $primary;
        text-style: bold;
        padding: 0 1;
    }

    EditorPanel #editor-footer {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $secondary;
        padding: 0 1;
    }

    EditorPanel TextArea {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "save", "Save"),
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+d", "save_recreate", "Save & Recreate"),
    ]

    def __init__(
        self,
        file_path: Path,
        stack_name: str,
        language: str | None = "yaml",
    ) -> None:
        super().__init__()
        self._file_path = file_path
        self._stack_name = stack_name
        self._language = language
        self._original_content = ""

    def compose(self) -> ComposeResult:
        yield Static(f" Editing: {self._file_path}", id="editor-header")
        yield TextArea(id="editor-area")
        yield Static(
            " Ctrl+S Save  |  Ctrl+D Save & Recreate  |  Esc Cancel",
            id="editor-footer",
        )

    def on_mount(self) -> None:
        editor = self.query_one("#editor-area", TextArea)
        if self._language:
            editor.language = self._language
        if self._file_path.exists():
            self._original_content = self._file_path.read_text()
        else:
            self._original_content = ""
        editor.text = self._original_content

    def _get_text(self) -> str:
        return self.query_one("#editor-area", TextArea).text

    def _is_modified(self) -> bool:
        return self._get_text() != self._original_content

    def _validate_yaml(self, text: str) -> bool:
        if self._language != "yaml":
            return True
        try:
            yaml.safe_load(text)
            return True
        except yaml.YAMLError as e:
            self.notify(f"Invalid YAML: {e}", severity="error")
            return False

    def _backup(self) -> None:
        if not self._file_path.exists():
            return
        backup_dir = Path("data/backups") / self._stack_name
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
        backup_path = backup_dir / f"{timestamp}.yml"
        backup_path.write_text(self._original_content)

    def _save(self) -> bool:
        text = self._get_text()
        if not self._validate_yaml(text):
            return False
        self._backup()
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(text)
        self._original_content = text
        return True

    def action_save(self) -> None:
        if self._save():
            self.notify("Saved")
            self.dismiss("saved")

    def action_save_recreate(self) -> None:
        if self._save():
            self.notify("Saved — recreating stack...")
            self.dismiss("recreate")

    def action_cancel(self) -> None:
        if self._is_modified():
            from dockmeister.screens.confirm import ConfirmDialog

            def on_confirm(result: bool) -> None:
                if result:
                    self.dismiss(None)

            self.app.push_screen(
                ConfirmDialog("Discard unsaved changes?"),
                on_confirm,
            )
        else:
            self.dismiss(None)
