"""Slash fallthrough handler tests (Prompt 205)."""

from __future__ import annotations

import httpx
import pytest

from keprix.tui.slash_handler import dispatch_slash_with_fallthrough, sanitize_slash_output
from keprix.tui.slash_registry import LOCAL_SLASH_COMMANDS
from keprix.tui.app import KeprixTuiApp
from keprix.tui.client import KeprixClient


FORBIDDEN_DEBUG_COPY = (
    "Traceback",
    "AttributeError",
    "HTTPStatusError",
    "user_id:",
    "workspace_id:",
    "channel_user_id:",
    "role: admin",
    "channel: tui",
)


class _StubClient:
    def __init__(self) -> None:
        self.exec_calls: list[tuple[str, str]] = []
        self.dispatch_calls: list[tuple[str, str, str]] = []
        self.exec_result: dict = {"ok": True, "output": "backend output", "pager": False}
        self.dispatch_result: dict = {"type": "exec", "output": "dispatch output"}

    async def slash_exec(self, command: str, *, session_id: str = "") -> dict:
        self.exec_calls.append((command, session_id))
        return dict(self.exec_result)

    async def command_dispatch(self, name: str, arg: str, *, session_id: str = "") -> dict:
        self.dispatch_calls.append((name, arg, session_id))
        return dict(self.dispatch_result)


@pytest.mark.asyncio
async def test_local_help_never_hits_network() -> None:
    client = _StubClient()

    async def _noop() -> None:
        return None

    result = await dispatch_slash_with_fallthrough(
        "/help",
        client=client,
        session_id="s1",
        request_session_id="s1",
        on_quit=_noop,
        on_model=_noop,
        on_clear=_noop,
        on_copy=_noop,
        on_interrupt=_noop,
        queue_snapshot=list,
    )
    assert result.handled is True
    assert "Local TUI commands" in result.message
    assert client.exec_calls == []


@pytest.mark.asyncio
async def test_timeline_is_local_and_never_hits_network() -> None:
    client = _StubClient()

    async def _noop() -> None:
        return None

    async def _timeline(_args: list[str]):
        return type("Result", (), {"handled": True, "message": "Timeline ok"})()

    result = await dispatch_slash_with_fallthrough(
        "/timeline",
        client=client,
        session_id="s1",
        request_session_id="s1",
        on_quit=_noop,
        on_model=_noop,
        on_clear=_noop,
        on_copy=_noop,
        on_interrupt=_noop,
        on_timeline=_timeline,
        queue_snapshot=list,
    )

    assert result.handled is True
    assert result.message == "Timeline ok"
    assert client.exec_calls == []
    assert client.dispatch_calls == []


@pytest.mark.asyncio
async def test_backend_memory_search_calls_exec() -> None:
    client = _StubClient()

    async def _noop() -> None:
        return None

    result = await dispatch_slash_with_fallthrough(
        "/memory search widgets",
        client=client,
        session_id="s1",
        request_session_id="s1",
        on_quit=_noop,
        on_model=_noop,
        on_clear=_noop,
        on_copy=_noop,
        on_interrupt=_noop,
        queue_snapshot=list,
    )
    assert result.handled is True
    assert client.exec_calls == [("memory search widgets", "s1")]
    assert result.message == "backend output"


@pytest.mark.asyncio
async def test_fallthrough_dispatches_unknown_skill_path() -> None:
    client = _StubClient()
    client.exec_result = {"ok": False, "fallthrough": True, "output": ""}
    client.dispatch_result = {"type": "exec", "output": "skill output"}

    async def _noop() -> None:
        return None

    result = await dispatch_slash_with_fallthrough(
        "/zzz something",
        client=client,
        session_id="s1",
        request_session_id="s1",
        on_quit=_noop,
        on_model=_noop,
        on_clear=_noop,
        on_copy=_noop,
        on_interrupt=_noop,
        queue_snapshot=list,
    )
    assert client.dispatch_calls == [("zzz", "something", "s1")]
    assert result.message == "skill output"


@pytest.mark.asyncio
async def test_stale_session_guard_drops_exec_response() -> None:
    client = _StubClient()
    client.exec_result = {"ok": True, "output": "late", "pager": False}

    async def _noop() -> None:
        return None

    result = await dispatch_slash_with_fallthrough(
        "/status",
        client=client,
        session_id="s-new",
        request_session_id="s-old",
        on_quit=_noop,
        on_model=_noop,
        on_clear=_noop,
        on_copy=_noop,
        on_interrupt=_noop,
        queue_snapshot=list,
    )
    assert result.handled is True
    assert result.message == ""


@pytest.mark.asyncio
async def test_fuzzy_local_alias_runs_local_command_without_backend() -> None:
    client = _StubClient()
    cleared = False

    async def _noop() -> None:
        return None

    async def _clear() -> None:
        nonlocal cleared
        cleared = True

    result = await dispatch_slash_with_fallthrough(
        "/clr",
        client=client,
        session_id="s1",
        request_session_id="s1",
        on_quit=_noop,
        on_model=_noop,
        on_clear=_clear,
        on_copy=_noop,
        on_interrupt=_noop,
        queue_snapshot=list,
    )
    assert result.handled is True
    assert cleared is True
    assert client.exec_calls == []
    assert client.dispatch_calls == []


@pytest.mark.asyncio
async def test_backend_dispatch_http_error_returns_message() -> None:
    class ErrorClient(_StubClient):
        async def command_dispatch(self, name: str, arg: str, *, session_id: str = "") -> dict:
            request = httpx.Request("POST", "http://127.0.0.1/api/command/dispatch")
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError("not found", request=request, response=response)

    client = ErrorClient()
    client.exec_result = {"ok": False, "fallthrough": True, "output": ""}

    async def _noop() -> None:
        return None

    result = await dispatch_slash_with_fallthrough(
        "/unknown",
        client=client,
        session_id="s1",
        request_session_id="s1",
        on_quit=_noop,
        on_model=_noop,
        on_clear=_noop,
        on_copy=_noop,
        on_interrupt=_noop,
        queue_snapshot=list,
    )
    assert result.handled is True
    assert "Command /unknown is not available" in result.message


@pytest.mark.asyncio
async def test_backend_dispatch_http_error_does_not_show_exception_class() -> None:
    class ErrorClient(_StubClient):
        async def command_dispatch(self, name: str, arg: str, *, session_id: str = "") -> dict:
            request = httpx.Request("POST", "http://127.0.0.1/api/command/dispatch")
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError("not found", request=request, response=response)

    client = ErrorClient()
    client.exec_result = {"ok": False, "fallthrough": True, "output": ""}

    async def _noop() -> None:
        return None

    result = await dispatch_slash_with_fallthrough(
        "/doctor",
        client=client,
        session_id="s1",
        request_session_id="s1",
        on_quit=_noop,
        on_model=_noop,
        on_clear=_noop,
        on_copy=_noop,
        on_interrupt=_noop,
        queue_snapshot=list,
    )
    assert result.handled is True
    assert "Doctor is not available" in result.message
    assert "HTTPStatusError" not in result.message


def test_sanitize_slash_output_removes_backend_context_fields() -> None:
    output = sanitize_slash_output(
        "\n".join(
            [
                "Transcript cleared.",
                "user_id: adad9243-955c-42d1-a876-4c806e554679",
                "workspace_id: default",
                "role: admin",
                "channel: tui",
                "channel_user_id: adad9243-955c-42d1-a876-4c806e554679",
                "Command failed with HTTPStatusError",
            ]
        )
    )

    assert "Transcript cleared." in output
    assert "user_id:" not in output
    assert "workspace_id:" not in output
    assert "channel_user_id:" not in output
    assert "HTTPStatusError" not in output
    assert "backend HTTP error" in output


@pytest.mark.asyncio
@pytest.mark.parametrize("command", [name for item in LOCAL_SLASH_COMMANDS for name in item.names])
async def test_all_registered_slash_commands_hide_error_and_debug_copy(command: str) -> None:
    class ErrorDebugClient(_StubClient):
        async def slash_exec(self, command: str, *, session_id: str = "") -> dict:
            self.exec_calls.append((command, session_id))
            return {
                "ok": True,
                "output": "\n".join(
                    [
                        "Command diagnostic",
                        "user_id: adad9243-955c-42d1-a876-4c806e554679",
                        "workspace_id: default",
                        "role: admin",
                        "channel: tui",
                        "channel_user_id: adad9243-955c-42d1-a876-4c806e554679",
                        "HTTPStatusError",
                    ]
                ),
            }

        async def command_dispatch(self, name: str, arg: str, *, session_id: str = "") -> dict:
            self.dispatch_calls.append((name, arg, session_id))
            return {
                "type": "exec",
                "output": "\n".join(
                    [
                        "Dispatch diagnostic",
                        "user_id: adad9243-955c-42d1-a876-4c806e554679",
                        "workspace_id: default",
                        "HTTPStatusError",
                    ]
                ),
            }

    client = ErrorDebugClient()
    callbacks: list[str] = []

    async def _noop() -> None:
        callbacks.append("noop")

    async def _details(_args: list[str]):
        return type("Result", (), {"handled": True, "message": "Details ok"})()

    async def _voice(_args: list[str]):
        return type("Result", (), {"handled": True, "message": "Voice ok"})()

    async def _steer(_text: str):
        return type("Result", (), {"handled": True, "message": "Steer ok"})()

    result = await dispatch_slash_with_fallthrough(
        command,
        client=client,
        session_id="s1",
        request_session_id="s1",
        on_quit=_noop,
        on_model=_noop,
        on_clear=_noop,
        on_copy=_noop,
        on_interrupt=_noop,
        on_new=_noop,
        on_sessions=_noop,
        on_reconnect=_noop,
        on_toggle_mouse=_noop,
        on_details=_details,
        on_voice=_voice,
        on_steer=_steer,
        queue_snapshot=list,
    )

    assert result.handled is True
    visible = "\n".join([result.message, result.submit_text, result.alias_command])
    for forbidden in FORBIDDEN_DEBUG_COPY:
        assert forbidden not in visible, command


@pytest.mark.asyncio
async def test_debug_slash_avoids_raw_identifiers(monkeypatch) -> None:
    app = KeprixTuiApp(client=KeprixClient(), session_id="adad9243-955c-42d1-a876-4c806e554679")
    app.connected = True
    app._setup_required = False
    output: list[str] = []
    monkeypatch.setattr(app, "_log_system", output.append)

    await app._submit_text("/debug")

    assert output
    assert "Debug state" in output[-1]
    assert "session_id:" not in output[-1]
    assert "adad9243-955c-42d1-a876-4c806e554679" not in output[-1]
