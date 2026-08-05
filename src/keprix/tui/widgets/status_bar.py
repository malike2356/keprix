"""Operational bottom status bar."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from keprix.tui.command_center.status import StatusSnapshot, render_status_bar


class StatusBar(Horizontal):
    """Stable-width bottom status bar with runtime health."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: bottom;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
    }
    #status-line {
        width: 1fr;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.snapshot = StatusSnapshot()
        self.width_hint = 120

    def compose(self) -> ComposeResult:
        yield Static(render_status_bar(self.snapshot, width=self.width_hint), id="status-line")

    def update_snapshot(self, snapshot: StatusSnapshot, *, width: int | None = None) -> None:
        self.snapshot = snapshot
        if width is not None:
            self.width_hint = max(40, width)
        line = render_status_bar(self.snapshot, width=self.width_hint)
        self.query_one("#status-line", Static).update(line)

    def set_connected(self, connected: bool) -> None:
        self.update_snapshot(StatusSnapshot(**{**self.snapshot.__dict__, "backend_healthy": connected}))

    def set_agent_busy(self, busy: bool) -> None:
        self.update_snapshot(StatusSnapshot(**{**self.snapshot.__dict__, "agent_busy": busy}))
