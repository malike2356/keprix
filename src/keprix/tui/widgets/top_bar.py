"""Top bar widget for keprix TUI.

Displays: session title, model badge, token usage, clock, and help hint.
Matches Hermes's appChrome.tsx / top bar pattern.
"""

from __future__ import annotations

import time
from datetime import datetime

from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import Horizontal


class TopBar(Horizontal):
    """Top bar with session metadata and status indicators."""

    DEFAULT_CSS = """
    TopBar {
        height: 1;
        dock: top;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
    }
    TopBar > Static {
        width: auto;
        margin: 0 1;
    }
    """

    def __init__(
        self,
        session_title: str = "New Session",
        model_name: str = "",
        token_count: int = 0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._session_title = session_title
        self._model_name = model_name
        self._token_count = token_count
        self._clock = ""

    def compose(self) -> ComposeResult:
        yield Static(self._render_title(), id="topbar-title")
        yield Static(self._render_model(), id="topbar-model")
        yield Static(self._render_tokens(), id="topbar-tokens")
        yield Static(self._render_clock(), id="topbar-clock")

    def update_title(self, title: str) -> None:
        self._session_title = title
        title_w = self.query_one("#topbar-title", Static)
        title_w.update(self._render_title())

    def update_model(self, model: str) -> None:
        self._model_name = model
        model_w = self.query_one("#topbar-model", Static)
        model_w.update(self._render_model())

    def update_tokens(self, count: int) -> None:
        self._token_count = count
        token_w = self.query_one("#topbar-tokens", Static)
        token_w.update(self._render_tokens())

    def tick_clock(self) -> None:
        """Called on timer to update the clock."""
        self._clock = datetime.now().strftime("%H:%M")
        try:
            clock_w = self.query_one("#topbar-clock", Static)
            clock_w.update(self._render_clock())
        except Exception:
            pass

    def _render_title(self) -> str:
        title = self._session_title or "keprix"
        if len(title) > 30:
            title = title[:27] + "..."
        return f"[bold]{title}[/]"

    def _render_model(self) -> str:
        if not self._model_name:
            return ""
        return f"[dim]{self._model_name}[/]"

    def _render_tokens(self) -> str:
        if self._token_count <= 0:
            return ""
        return f"[dim]tokens {_format_tokens(self._token_count)}[/]"

    def _render_clock(self) -> str:
        return f"[dim]{self._clock}[/]"


class StatusBar(Horizontal):
    """Bottom status bar with connection and agent state."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: bottom;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._connected = False
        self._agent_busy = False
        self._input_mode = "insert"

    def compose(self) -> ComposeResult:
        yield Static(self._render_connection(), id="status-connection")
        yield Static(self._render_agent(), id="status-agent")
        yield Static(self._render_mode(), id="status-mode")

    def set_connected(self, connected: bool) -> None:
        self._connected = connected
        w = self.query_one("#status-connection", Static)
        w.update(self._render_connection())

    def set_agent_busy(self, busy: bool) -> None:
        self._agent_busy = busy
        w = self.query_one("#status-agent", Static)
        w.update(self._render_agent())

    def _render_connection(self) -> str:
        if self._connected:
            return "[green]online[/] Connected"
        return "[red]offline[/] Disconnected"

    def _render_agent(self) -> str:
        if self._agent_busy:
            return "[yellow]busy[/] Busy"
        return "[dim]idle[/] Idle"

    def _render_mode(self) -> str:
        return f"[dim]{self._input_mode.upper()}[/]"


def _format_tokens(count: int) -> str:
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)
