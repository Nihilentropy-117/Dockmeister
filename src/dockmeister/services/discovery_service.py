from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

COMPOSE_FILENAMES = {
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
}


class _StackEventHandler(FileSystemEventHandler):
    def __init__(self, on_change: Callable[[], None]) -> None:
        super().__init__()
        self._on_change = on_change
        self._debounce_timer: threading.Timer | None = None

    def _debounced_change(self) -> None:
        if self._debounce_timer:
            self._debounce_timer.cancel()
        self._debounce_timer = threading.Timer(1.0, self._on_change)
        self._debounce_timer.daemon = True
        self._debounce_timer.start()

    def on_created(self, event: FileSystemEvent) -> None:
        self._debounced_change()

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._debounced_change()

    def on_moved(self, event: FileSystemEvent) -> None:
        self._debounced_change()


class DiscoveryService:
    def __init__(self, stacks_dir: Path, on_change: Callable[[], None]) -> None:
        self.stacks_dir = stacks_dir
        self._on_change = on_change
        self._observer: Observer | None = None
        self._poll_thread: threading.Thread | None = None
        self._poll_stop = threading.Event()
        self._known_stacks: set[str] = set()

    def scan(self) -> list[str]:
        stacks: list[str] = []
        if not self.stacks_dir.exists():
            return stacks
        for entry in sorted(self.stacks_dir.iterdir()):
            if not entry.is_dir():
                continue
            for compose_name in COMPOSE_FILENAMES:
                if (entry / compose_name).exists():
                    stacks.append(entry.name)
                    break
        return stacks

    def start_watching(self) -> None:
        try:
            handler = _StackEventHandler(self._on_change)
            self._observer = Observer()
            self._observer.schedule(handler, str(self.stacks_dir), recursive=True)
            self._observer.daemon = True
            self._observer.start()
        except Exception:
            self._start_polling()

    def _start_polling(self) -> None:
        self._poll_stop.clear()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self) -> None:
        self._known_stacks = set(self.scan())
        while not self._poll_stop.is_set():
            time.sleep(5)
            current = set(self.scan())
            if current != self._known_stacks:
                self._known_stacks = current
                self._on_change()

    def stop_watching(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None
        self._poll_stop.set()
        if self._poll_thread:
            self._poll_thread.join(timeout=2)
            self._poll_thread = None
