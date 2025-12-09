from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Static

from dockmeister.models.container import Container, ContainerStats
from dockmeister.models.stack import Stack, StackStatus


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "K", "M", "G", "T"):
        if abs(n) < 1024:
            if unit == "B":
                return f"{n}{unit}"
            return f"{n:.1f}{unit}"
        n //= 1024
    return f"{n}P"


class DetailPanel(Widget):
    DEFAULT_CSS = """
    DetailPanel {
        height: 1fr;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._current_stack: Stack | None = None

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(" Select a stack", id="detail-header", classes="panel-title"),
            Static("", id="detail-containers"),
            Static("", id="detail-info"),
            id="detail-content",
        )

    def show_stack(self, stack: Stack) -> None:
        self._current_stack = stack
        header = self.query_one("#detail-header", Static)

        status_text = stack.status.value.upper()
        healthy = stack.healthy_count
        total = len(stack.containers)
        health_text = f" \u2014 {healthy}/{total} healthy" if total > 0 else ""
        header.update(f" {stack.name} \u2014 {status_text}{health_text}")

        self._render_containers(stack.containers)
        self._render_info(stack)

    def _render_containers(self, containers: list[Container]) -> None:
        widget = self.query_one("#detail-containers", Static)
        if not containers:
            widget.update(" No containers")
            return

        lines = [" CONTAINERS          CPU    MEM     NET"]
        for i, c in enumerate(containers, 1):
            name = c.name[:18].ljust(18)
            cpu = f"{c.cpu_percent:5.1f}%"
            mem = _fmt_bytes(c.mem_usage_bytes).rjust(6)
            net = c.net_io.rjust(8)
            status_color = "green" if c.status == "running" else "red"
            lines.append(
                f" [{status_color}]{i}[/] {name} {cpu} {mem} {net}"
            )
        widget.update("\n".join(lines))

    def _render_info(self, stack: Stack) -> None:
        widget = self.query_one("#detail-info", Static)
        all_ports: list[str] = []
        all_vols: list[str] = []
        all_nets: list[str] = []
        for c in stack.containers:
            all_ports.extend(c.ports)
            all_vols.extend(c.volumes)
            all_nets.extend(c.networks)

        ports = "  ".join(sorted(set(all_ports))) or "\u2014"
        vols = "  ".join(sorted(set(all_vols))) or "\u2014"
        nets = "  ".join(sorted(set(all_nets))) or "\u2014"

        widget.update(
            f" PORTS  {ports}\n"
            f" VOLS   {vols}\n"
            f" NETS   {nets}"
        )

    def update_stats(self, stats: dict[str, ContainerStats]) -> None:
        if not self._current_stack:
            return
        for c in self._current_stack.containers:
            if c.id in stats:
                s = stats[c.id]
                c.cpu_percent = s.cpu_percent
                c.mem_usage_bytes = s.mem_usage_bytes
                c.mem_usage = _fmt_bytes(s.mem_usage_bytes)
                c.net_io = f"{_fmt_bytes(s.net_rx_bytes)}/{_fmt_bytes(s.net_tx_bytes)}"
        self._render_containers(self._current_stack.containers)
