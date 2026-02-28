from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static
from textual import work
from textual.worker import get_current_worker


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


class PrunePanel(ModalScreen):
    DEFAULT_CSS = """
    PrunePanel {
        align: center middle;
    }

    PrunePanel > Vertical {
        width: 60;
        height: auto;
        max-height: 80%;
        border: solid $secondary;
        background: $surface;
        padding: 1 2;
    }

    PrunePanel #prune-title {
        text-style: bold;
        text-align: center;
        height: 1;
        margin-bottom: 1;
    }

    PrunePanel #prune-info {
        height: auto;
        margin-bottom: 1;
    }

    PrunePanel #prune-footer {
        dock: bottom;
        height: 1;
        text-align: center;
        color: $secondary;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Close"),
        Binding("i", "prune_images", "Prune Images"),
        Binding("c", "prune_containers", "Prune Containers"),
        Binding("v", "prune_volumes", "Prune Volumes"),
        Binding("n", "prune_networks", "Prune Networks"),
        Binding("b", "prune_build_cache", "Prune Build Cache"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("System Prune", id="prune-title")
            yield Static("Loading disk usage...", id="prune-info")
            yield Static(
                "\\[i]mages \\[c]ontainers \\[v]olumes \\[n]etworks \\[b]uild cache  Esc close",
                id="prune-footer",
            )

    def on_mount(self) -> None:
        self._load_df()

    @work(thread=True)
    def _load_df(self) -> None:
        worker = get_current_worker()
        try:
            df = self.app.docker_service.system_df()
        except Exception:
            df = {}

        if worker.is_cancelled:
            return

        images = df.get("Images", []) or []
        containers = df.get("Containers", []) or []
        volumes = df.get("Volumes", []) or []
        build_cache = df.get("BuildCache", []) or []

        dangling_images = [i for i in images if i.get("Containers", 0) == 0]
        stopped_containers = [c for c in containers if c.get("State") != "running"]
        unused_volumes = [v for v in volumes if v.get("UsageData", {}).get("RefCount", 0) == 0]

        img_size = sum(i.get("Size", 0) for i in dangling_images)
        cont_size = sum(c.get("SizeRw", 0) or 0 for c in stopped_containers)
        vol_size = sum(v.get("UsageData", {}).get("Size", 0) for v in unused_volumes)
        cache_size = sum(b.get("Size", 0) for b in build_cache if not b.get("InUse"))

        info = (
            f"  Images (dangling):    {len(dangling_images):>4}    {_fmt_size(img_size):>10}\n"
            f"  Containers (stopped): {len(stopped_containers):>4}    {_fmt_size(cont_size):>10}\n"
            f"  Volumes (unused):     {len(unused_volumes):>4}    {_fmt_size(vol_size):>10}\n"
            f"  Build cache (unused):          {_fmt_size(cache_size):>10}\n"
        )
        self.app.call_from_thread(self.query_one("#prune-info", Static).update, info)

    def _do_prune(self, resource: str) -> None:
        from dockmeister.screens.confirm import ConfirmDialog

        def on_confirm(result: bool) -> None:
            if result:
                self._run_prune(resource)

        self.app.push_screen(
            ConfirmDialog(f"Prune {resource}?", destructive=True),
            on_confirm,
        )

    @work(thread=True)
    def _run_prune(self, resource: str) -> None:
        worker = get_current_worker()
        try:
            client = self.app.docker_service.client
            if resource == "images":
                result = client.images.prune(filters={"dangling": True})
                reclaimed = result.get("SpaceReclaimed", 0)
            elif resource == "containers":
                result = client.containers.prune()
                reclaimed = result.get("SpaceReclaimed", 0)
            elif resource == "volumes":
                result = client.volumes.prune()
                reclaimed = result.get("SpaceReclaimed", 0)
            elif resource == "networks":
                client.networks.prune()
                reclaimed = 0
            elif resource == "build_cache":
                result = client.api.prune_builds()
                reclaimed = result.get("SpaceReclaimed", 0)
            else:
                return

            if not worker.is_cancelled:
                msg = f"Pruned {resource}"
                if reclaimed:
                    msg += f" — reclaimed {_fmt_size(reclaimed)}"
                self.app.call_from_thread(self.notify, msg)
                self._load_df()
        except Exception as e:
            if not worker.is_cancelled:
                self.app.call_from_thread(
                    self.notify, f"Prune error: {e}", severity="error"
                )

    def action_prune_images(self) -> None:
        self._do_prune("images")

    def action_prune_containers(self) -> None:
        self._do_prune("containers")

    def action_prune_volumes(self) -> None:
        self._do_prune("volumes")

    def action_prune_networks(self) -> None:
        self._do_prune("networks")

    def action_prune_build_cache(self) -> None:
        self._do_prune("build_cache")

    def action_cancel(self) -> None:
        self.dismiss()
