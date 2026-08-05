from __future__ import annotations

import pytest

from keprix.tui.app import KeprixTuiApp
from keprix.tui.client import KeprixClient
from keprix.tui.error_boundary import capture_errors
from keprix.tui.terminal_capabilities import TerminalCapabilities
from keprix.tui.terminal_startup import probe_terminal_startup


class _Status:
    def __init__(self) -> None:
        self.connected: bool | None = None

    def set_connected(self, connected: bool) -> None:
        self.connected = connected


class _Panel:
    def update(self, value: str) -> None:
        self.value = value

    def remove_class(self, name: str) -> None:
        return None

    def add_class(self, name: str) -> None:
        return None


@pytest.mark.asyncio
async def test_reconnect_offline_does_not_query_removed_status_widget() -> None:
    class Client(KeprixClient):
        async def health_check(self) -> bool:
            return False

    app = KeprixTuiApp(client=Client(), session_id="s1")
    status = _Status()
    messages: list[str] = []
    app._status_bar = lambda: status  # type: ignore[method-assign]
    app._log_system = messages.append  # type: ignore[method-assign]
    app._update_sidebar = lambda: None  # type: ignore[method-assign]

    await app.action_reconnect()

    assert status.connected is False
    assert any("Still offline" in message for message in messages)


@pytest.mark.asyncio
async def test_stream_exception_marks_runtime_errored_without_crashing() -> None:
    class Client(KeprixClient):
        async def stream_message(self, session_id: str, content: str):
            raise RuntimeError("stream failed")
            yield {}

    app = KeprixTuiApp(client=Client(), session_id="s1")
    messages: list[str] = []
    app._thinking_panel = lambda: _Panel()  # type: ignore[method-assign]
    app._set_busy = lambda busy: None  # type: ignore[method-assign]
    app._refresh_thinking_panel = lambda: None  # type: ignore[method-assign]
    app._log_system = messages.append  # type: ignore[method-assign]

    async def end_agent_stream() -> None:
        return None

    async def refresh_sessions() -> None:
        return None

    app._end_agent_stream = end_agent_stream  # type: ignore[method-assign]
    app.refresh_sessions = refresh_sessions  # type: ignore[method-assign]

    await app._run_turn("hello")

    assert app._runtime_store.turn.status == "errored"
    assert any("stream failed" in message for message in messages)


def test_error_boundary_captures_render_errors() -> None:
    def fail() -> str:
        raise RuntimeError("render failed")

    value, error = capture_errors(fail)

    assert value is None
    assert error is not None
    assert error.message == "render failed"
    assert "RuntimeError" in error.stack


def test_termux_terminal_profile_degrades_features(monkeypatch) -> None:
    caps = TerminalCapabilities(
        truecolor=False,
        osc52=False,
        alternate_screen=False,
        terminal_name="termux",
        is_termux=True,
    )
    monkeypatch.setattr("keprix.tui.terminal_startup.get_terminal_capabilities", lambda: caps)

    profile = probe_terminal_startup()

    assert profile.simplified_ui is True
    assert "Termux mode" in profile.notes[0]
