from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Static
from textual import work
from textual.worker import get_current_worker, Worker

from dockmeister.models.container import Container
from dockmeister.models.stack import Stack, StackMeta, StackStatus
from dockmeister.screens.confirm import ConfirmDialog
from dockmeister.widgets.detail_panel import DetailPanel
from dockmeister.widgets.log_viewer import LogViewer
from dockmeister.widgets.stack_list import StackListPanel


class MainScreen(Screen):
    BINDINGS = [
        Binding("q", "app.quit", "Quit", priority=True),
        Binding("t", "toggle_theme", "Theme", priority=True),
        Binding("u", "stack_up", "Up", priority=True),
        Binding("d", "stack_down", "Down", priority=True),
        Binding("r", "stack_restart", "Restart", priority=True),
        Binding("p", "stack_pull", "Pull", priority=True),
        Binding("R", "stack_recreate", "Recreate", key_display="R", priority=True),
        Binding("U", "up_all", "Up All", key_display="U", priority=True),
        Binding("P", "pull_all", "Pull All", key_display="P", priority=True),
        Binding("D", "down_all", "Down All", key_display="D", priority=True),
        Binding("e", "edit_compose", "Edit", priority=True),
        Binding("E", "edit_env", "Edit .env", key_display="E", priority=True),
        Binding("l", "toggle_logs", "Logs", priority=True),
        Binding("s", "shell", "Shell", priority=True),
        Binding("f", "toggle_favorite", "Fav", priority=True),
        Binding("x", "toggle_enabled", "En/Dis", priority=True),
        Binding("slash", "search", "Search", key_display="/", priority=True),
        Binding("question_mark", "help", "Help", key_display="?", priority=True),
        Binding("h", "history", "History", priority=True),
        Binding("ctrl+p", "prune", "Prune", key_display="C-p", priority=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._stacks: list[Stack] = []
        self._selected_stack: Stack | None = None
        self._selected_container_idx: int = 0
        self._active_ops: set[str] = set()

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

    def on_mount(self) -> None:
        if not self.app._docker_available:
            self.notify(
                "Docker not available. Check that the Docker socket is mounted.",
                severity="error",
                timeout=10,
            )
        self.app.start_discovery(on_change=self._on_fs_change)
        self._load_stacks()
        self._check_updates()

    def _on_fs_change(self) -> None:
        self.app.call_from_thread(self._load_stacks)

    # --- Stack scanning ---

    @work(thread=True, exclusive=True, group="scan")
    def _load_stacks(self) -> None:
        worker = get_current_worker()
        discovery = self.app._discovery
        if not discovery:
            return

        stack_names = discovery.scan()
        stacks: list[Stack] = []

        for name in stack_names:
            if worker.is_cancelled:
                return
            stack_path = self.app.stacks_dir / name
            stack = Stack(name=name, path=stack_path)

            containers = self.app.docker_service.list_containers(project=name)
            stack.containers = containers

            if not containers:
                stack.status = StackStatus.DOWN
            elif all(c.status == "running" for c in containers):
                stack.status = StackStatus.UP
            elif any(c.status == "running" for c in containers):
                stack.status = StackStatus.PARTIAL
            else:
                stack.status = StackStatus.DOWN

            stacks.append(stack)

        if worker.is_cancelled:
            return

        self.app.call_from_thread(self._apply_metadata_and_refresh, stacks)

    def _apply_metadata_and_refresh(self, stacks: list[Stack]) -> None:
        self.run_worker(self._apply_metadata(stacks), exclusive=True, group="metadata")

    async def _apply_metadata(self, stacks: list[Stack]) -> None:
        all_meta = await self.app.db.get_all_stack_meta()
        meta_map = {m.name: m for m in all_meta}

        for stack in stacks:
            if stack.name in meta_map:
                meta = meta_map[stack.name]
                stack.favorite = meta.favorite
                stack.enabled = meta.enabled
                stack.tags = json.loads(meta.tags) if meta.tags else []
                stack.notes = meta.notes

        self._stacks = stacks
        self._update_header()
        self.query_one(StackListPanel).refresh_stacks(stacks)

        if self._selected_stack:
            for s in stacks:
                if s.name == self._selected_stack.name:
                    self._selected_stack = s
                    self.query_one(DetailPanel).show_stack(s)
                    break

    def _update_header(self) -> None:
        total = len(self._stacks)
        running = sum(
            len([c for c in s.containers if c.status == "running"])
            for s in self._stacks
        )
        header = self.query_one("#header-bar", Static)
        header.update(
            f" Dockmeister v0.1              \u25b8 {total} stacks \u2502 {running} running"
        )

    def _get_selected_name(self) -> str | None:
        return self._selected_stack.name if self._selected_stack else None

    # --- Theme ---

    def action_toggle_theme(self) -> None:
        self.app.theme = "p3" if self.app.theme == "p1" else "p1"

    # --- Lifecycle operations ---

    def _check_op_guard(self, name: str) -> bool:
        if name in self._active_ops:
            self.notify(f"Operation already in progress for {name}", severity="warning")
            return False
        return True

    @work(thread=True)
    def _run_compose_op(self, stack_name: str, op: str) -> None:
        worker = get_current_worker()
        self._active_ops.add(stack_name)
        try:
            getattr(self.app.compose_service, op)(stack_name)
            if not worker.is_cancelled:
                self.app.call_from_thread(
                    self.notify, f"{op} completed: {stack_name}"
                )
                self.app.call_from_thread(self._log_and_refresh, stack_name, op)
        except Exception as e:
            if not worker.is_cancelled:
                self.app.call_from_thread(
                    self.notify, f"Error ({op} {stack_name}): {e}", severity="error"
                )
        finally:
            self._active_ops.discard(stack_name)

    def _log_and_refresh(self, stack_name: str, action: str) -> None:
        self.run_worker(self._async_log(stack_name, action))
        self._load_stacks()

    async def _async_log(self, stack_name: str, action: str) -> None:
        compose_snapshot = None
        try:
            stack = next((s for s in self._stacks if s.name == stack_name), None)
            if stack and stack.compose_file.exists():
                compose_snapshot = stack.compose_file.read_text()
        except Exception:
            pass
        await self.app.db.log_action(stack_name, action, compose_snapshot=compose_snapshot)

    def action_stack_up(self) -> None:
        name = self._get_selected_name()
        if name and self._check_op_guard(name):
            self.notify(f"Starting {name}...")
            self._run_compose_op(name, "up")

    def action_stack_down(self) -> None:
        name = self._get_selected_name()
        if name and self._check_op_guard(name):
            self.notify(f"Stopping {name}...")
            self._run_compose_op(name, "down")

    def action_stack_restart(self) -> None:
        name = self._get_selected_name()
        if name and self._check_op_guard(name):
            self.notify(f"Restarting {name}...")
            self._run_compose_op(name, "restart")

    def action_stack_pull(self) -> None:
        name = self._get_selected_name()
        if name and self._check_op_guard(name):
            self.notify(f"Pulling images for {name}...")
            self._run_compose_op(name, "pull")

    @work(thread=True)
    def _run_recreate(self, stack_name: str) -> None:
        worker = get_current_worker()
        self._active_ops.add(stack_name)
        try:
            self.app.compose_service.pull(stack_name)
            if worker.is_cancelled:
                return
            self.app.compose_service.down(stack_name)
            if worker.is_cancelled:
                return
            self.app.compose_service.up(stack_name)
            if not worker.is_cancelled:
                self.app.call_from_thread(
                    self.notify, f"Recreate completed: {stack_name}"
                )
                self.app.call_from_thread(self._log_and_refresh, stack_name, "recreate")
        except Exception as e:
            if not worker.is_cancelled:
                self.app.call_from_thread(
                    self.notify,
                    f"Error (recreate {stack_name}): {e}",
                    severity="error",
                )
        finally:
            self._active_ops.discard(stack_name)

    def action_stack_recreate(self) -> None:
        name = self._get_selected_name()
        if name and self._check_op_guard(name):
            self.notify(f"Recreating {name} (pull + down + up)...")
            self._run_recreate(name)

    # --- Global operations ---

    @work(thread=True)
    def _run_global_op(self, op: str, stacks: list[Stack]) -> None:
        worker = get_current_worker()
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(getattr(self.app.compose_service, op), s.name): s
                for s in stacks
            }
            for future in as_completed(futures):
                if worker.is_cancelled:
                    return
                stack = futures[future]
                try:
                    future.result()
                    self.app.call_from_thread(
                        self.notify, f"{op}: {stack.name} done"
                    )
                except Exception as e:
                    self.app.call_from_thread(
                        self.notify,
                        f"{op}: {stack.name} failed: {e}",
                        severity="error",
                    )
        if not worker.is_cancelled:
            self.app.call_from_thread(self._load_stacks)

    def action_up_all(self) -> None:
        enabled = [s for s in self._stacks if s.enabled]
        if enabled:
            self.notify(f"Starting {len(enabled)} stacks...")
            self._run_global_op("up", enabled)

    def action_pull_all(self) -> None:
        if self._stacks:
            self.notify(f"Pulling {len(self._stacks)} stacks...")
            self._run_global_op("pull", self._stacks)

    def action_down_all(self) -> None:
        running = [s for s in self._stacks if s.status in (StackStatus.UP, StackStatus.PARTIAL)]
        if not running:
            self.notify("No running stacks")
            return

        def on_confirm(result: bool) -> None:
            if result:
                self.notify(f"Stopping {len(running)} stacks...")
                self._run_global_op("down", running)

        self.app.push_screen(
            ConfirmDialog(f"Stop all {len(running)} running stacks?", destructive=True),
            on_confirm,
        )

    # --- Favorites and enable/disable ---

    def action_toggle_favorite(self) -> None:
        name = self._get_selected_name()
        if name:
            self.run_worker(self._async_toggle_favorite(name))

    async def _async_toggle_favorite(self, name: str) -> None:
        is_fav = await self.app.db.toggle_favorite(name)
        for s in self._stacks:
            if s.name == name:
                s.favorite = is_fav
                break
        self.query_one(StackListPanel).refresh_stacks(self._stacks)
        self.notify(f"{'Favorited' if is_fav else 'Unfavorited'} {name}")

    def action_toggle_enabled(self) -> None:
        name = self._get_selected_name()
        if name:
            self.run_worker(self._async_toggle_enabled(name))

    async def _async_toggle_enabled(self, name: str) -> None:
        is_enabled = await self.app.db.toggle_enabled(name)
        for s in self._stacks:
            if s.name == name:
                s.enabled = is_enabled
                break
        self.query_one(StackListPanel).refresh_stacks(self._stacks)
        self.notify(f"{'Enabled' if is_enabled else 'Disabled'} {name}")

    # --- Search ---

    def action_search(self) -> None:
        self.query_one(StackListPanel).show_search()

    # --- Stats polling ---

    @work(thread=True, exclusive=True, group="stats")
    def _poll_stats(self) -> None:
        worker = get_current_worker()
        while not worker.is_cancelled:
            stack = self._selected_stack
            if stack and stack.containers:
                running = [c for c in stack.containers if c.status == "running"]
                if running:
                    container_ids = [c.id for c in running]
                    stats = self.app.stats_service.get_stats(container_ids)
                    if not worker.is_cancelled:
                        self.app.call_from_thread(
                            self.query_one(DetailPanel).update_stats, stats
                        )
            time.sleep(2)

    # --- Log streaming ---

    @work(thread=True, exclusive=True, group="log-stream")
    def _stream_logs(self, container_id: str, container_name: str) -> None:
        worker = get_current_worker()
        log_viewer = self.query_one(LogViewer)
        self.app.call_from_thread(log_viewer.clear_logs)
        self.app.call_from_thread(log_viewer.set_header, container_name)
        for chunk in self.app.docker_service.stream_logs(container_id, tail=100):
            if worker.is_cancelled:
                break
            try:
                line = chunk.decode("utf-8", errors="replace").strip()
            except AttributeError:
                line = str(chunk).strip()
            if line:
                self.app.call_from_thread(log_viewer.write_log, line)

    def _start_log_stream(self) -> None:
        if not self._selected_stack or not self._selected_stack.containers:
            return
        containers = self._selected_stack.containers
        idx = min(self._selected_container_idx, len(containers) - 1)
        c = containers[idx]
        if c.status == "running":
            self._stream_logs(c.id, c.name)

    def _select_container(self, idx: int) -> None:
        if not self._selected_stack:
            return
        containers = self._selected_stack.containers
        if 0 <= idx < len(containers):
            self._selected_container_idx = idx
            self._start_log_stream()

    def on_key(self, event) -> None:
        if event.character and event.character.isdigit():
            n = int(event.character)
            if 1 <= n <= 9:
                self._select_container(n - 1)

    def on_stack_list_panel_stack_selected(
        self, message: StackListPanel.StackSelected
    ) -> None:
        for s in self._stacks:
            if s.name == message.stack_name:
                self._selected_stack = s
                self._selected_container_idx = 0
                self.query_one(DetailPanel).show_stack(s)
                self._poll_stats()
                self._start_log_stream()
                break

    # --- Logs toggle ---

    def action_toggle_logs(self) -> None:
        log_viewer = self.query_one(LogViewer)
        log_viewer.focus()

    # --- Editor ---

    def action_edit_compose(self) -> None:
        stack = self._selected_stack
        if not stack:
            return
        from dockmeister.widgets.editor import EditorPanel

        def on_result(result: str | None) -> None:
            if result == "recreate" and stack:
                self.notify(f"Recreating {stack.name}...")
                self._run_recreate(stack.name)
            elif result == "saved":
                self._load_stacks()

        self.app.push_screen(
            EditorPanel(stack.compose_file, stack.name),
            on_result,
        )

    def action_edit_env(self) -> None:
        stack = self._selected_stack
        if not stack:
            return
        from dockmeister.widgets.editor import EditorPanel

        env_path = stack.env_file
        if not env_path.exists():
            env_path.touch()

        def on_result(result: str | None) -> None:
            if result == "recreate" and stack:
                self.notify(f"Recreating {stack.name}...")
                self._run_recreate(stack.name)

        self.app.push_screen(
            EditorPanel(env_path, stack.name, language=None),
            on_result,
        )

    # --- Help ---

    def action_help(self) -> None:
        from dockmeister.screens.help import HelpOverlay
        self.app.push_screen(HelpOverlay())

    # --- Shell ---

    def action_shell(self) -> None:
        if not self._selected_stack or not self._selected_stack.containers:
            self.notify("No container selected")
            return
        containers = self._selected_stack.containers
        idx = min(self._selected_container_idx, len(containers) - 1)
        c = containers[idx]
        if c.status != "running":
            self.notify(f"{c.name} is not running", severity="warning")
            return
        from dockmeister.widgets.shell import shell_into_container
        with self.app.suspend():
            shell_into_container(c.id)

    # --- History ---

    def action_history(self) -> None:
        from dockmeister.screens.history import HistoryScreen
        self.app.push_screen(HistoryScreen())

    # --- Prune ---

    def action_prune(self) -> None:
        from dockmeister.widgets.prune import PrunePanel
        self.app.push_screen(PrunePanel())

    # --- Update checker background ---

    @work(thread=True, exclusive=True, group="update-check")
    def _check_updates(self) -> None:
        worker = get_current_worker()
        while not worker.is_cancelled:
            for stack in self._stacks:
                if worker.is_cancelled:
                    return
                images = list({c.image for c in stack.containers if c.image})
                if not images:
                    continue
                # Run async check from thread
                self.app.call_from_thread(
                    self._run_update_check, stack.name, images
                )
            # Wait 30 minutes before next check
            for _ in range(1800):
                if worker.is_cancelled:
                    return
                time.sleep(1)

    def _run_update_check(self, stack_name: str, images: list[str]) -> None:
        self.run_worker(self._async_update_check(stack_name, images))

    async def _async_update_check(self, stack_name: str, images: list[str]) -> None:
        from dockmeister.services.update_checker import UpdateChecker
        checker = UpdateChecker(self.app.docker_service, self.app.db)
        results = await checker.check_stack_images(images)
        has_update = any(results.values())
        for s in self._stacks:
            if s.name == stack_name:
                s.has_update = has_update
                break
        self.query_one(StackListPanel).refresh_stacks(self._stacks)
