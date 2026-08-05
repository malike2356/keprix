"""Tests for TUI busy input modes (Prompt 201)."""

from __future__ import annotations

import pytest

from keprix.tui.app import KeprixTuiApp
from keprix.tui.client import KeprixClient, SteerNotBusyError
from keprix.tui.preferences import load_busy_input_override, save_busy_input_override
from keprix.tui.slash_commands import dispatch_slash


class _StubClient(KeprixClient):
    def __init__(self) -> None:
        super().__init__(base_url="http://127.0.0.1:3333")
        self.steer_calls: list[tuple[str, str]] = []
        self.interrupt_calls: list[str] = []
        self.steer_raises_not_busy = False

    async def steer(self, session_id: str, text: str) -> int:
        self.steer_calls.append((session_id, text))
        if self.steer_raises_not_busy:
            raise SteerNotBusyError(session_id)
        return len(text.strip())

    async def interrupt(self, session_id: str, *, keep_queue: bool = False) -> None:
        self.interrupt_calls.append(session_id)


@pytest.fixture
def tui_app(monkeypatch):
    monkeypatch.setattr("keprix.tui.preferences.load_busy_input_override", lambda: None)
    client = _StubClient()
    app = KeprixTuiApp(client=client, session_id="session-1")
    app.connected = True
    app.streaming = True
    app._config_busy_mode = "steer"
    app._log_system = lambda line: None  # type: ignore[method-assign]
    app._set_busy = lambda busy: None  # type: ignore[method-assign]
    app._update_status = lambda: None  # type: ignore[method-assign]
    return app, client


@pytest.mark.asyncio
async def test_steer_mode_submit_calls_steer_endpoint(tui_app) -> None:
    app, client = tui_app
    await app._handle_steer_submit("Focus on nginx only")
    assert client.steer_calls == [("session-1", "Focus on nginx only")]


@pytest.mark.asyncio
async def test_steer_mode_falls_back_when_not_busy(tui_app) -> None:
    app, client = tui_app
    client.steer_raises_not_busy = True
    started: list[str] = []

    async def _fake_start(text: str) -> None:
        started.append(text)

    app._start_turn = _fake_start  # type: ignore[method-assign]
    await app._handle_steer_submit("retry later")
    assert started == ["retry later"]


@pytest.mark.asyncio
async def test_interrupt_mode_submits_via_interrupt_path(tui_app) -> None:
    app, client = tui_app
    app._effective_busy_mode = lambda: "interrupt"  # type: ignore[method-assign]
    interrupted = False

    async def _fake_interrupt() -> None:
        nonlocal interrupted
        interrupted = True

    app.action_interrupt_turn = _fake_interrupt  # type: ignore[method-assign]
    await app._handle_interrupt_submit("new direction")
    assert interrupted is True
    assert app._pending_after_interrupt == "new direction"


@pytest.mark.asyncio
async def test_busy_slash_sets_local_mode(tui_app, tmp_path, monkeypatch) -> None:
    app, _client = tui_app
    prefs = tmp_path / "tui.json"
    monkeypatch.setattr("keprix.tui.preferences._prefs_path", lambda: prefs)

    app._local_busy_mode = None
    applied = await app._set_busy_mode("queue")
    assert applied == "queue"
    assert app._local_busy_mode == "queue"
    assert load_busy_input_override() == "queue"


@pytest.mark.asyncio
async def test_slash_busy_help_lists_modes() -> None:
    result = await dispatch_slash(
        "/busy",
        on_quit=asyncio_quit,
        on_model=asyncio_noop,
        on_clear=asyncio_noop,
        on_copy=asyncio_noop,
        on_interrupt=asyncio_noop,
        queue_snapshot=lambda: [],
        get_busy_mode=lambda: "steer",
    )
    assert result.handled is True
    assert "steer" in result.message


async def asyncio_quit() -> None:
    return None


async def asyncio_noop() -> None:
    return None


def test_effective_busy_mode_prefers_local_override(tui_app) -> None:
    app, _client = tui_app
    app._config_busy_mode = "queue"
    app._local_busy_mode = "steer"
    assert app._effective_busy_mode() == "steer"


def test_preferences_round_trip(tmp_path, monkeypatch) -> None:
    prefs = tmp_path / "tui.json"
    monkeypatch.setattr("keprix.tui.preferences._prefs_path", lambda: prefs)
    save_busy_input_override("steer")
    assert load_busy_input_override() == "steer"
