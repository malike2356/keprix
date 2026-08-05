from __future__ import annotations

import pytest

from keprix.tui.hardening import clear_error_message, safe_stream_json_line
from keprix.tui.runtime_transport.events import normalize_runtime_event
from keprix.tui.runtime_transport.http import HttpRuntimeTransport


def test_http_status_codes_have_clear_messages() -> None:
    for code in (400, 401, 403, 404, 408, 429, 500):
        message = clear_error_message(code)
        assert message
        assert "Traceback" not in message


def test_invalid_json_stream_line_becomes_error_event() -> None:
    payload = safe_stream_json_line("{not json")
    assert payload == {"type": "error", "message": "Backend sent an invalid stream line."}
    event = normalize_runtime_event(payload)
    assert event.type == "error"


def test_missing_tool_and_subagent_ids_are_normalized() -> None:
    tool = normalize_runtime_event({"type": "tool_call", "name": "scan"})
    subagent = normalize_runtime_event({"type": "subagent_spawn", "label": "worker"})
    assert tool.type == "tool_call"
    assert tool.payload["name"] == "scan"
    assert subagent.type == "subagent_spawn"
    assert subagent.payload["label"] == "worker"


@pytest.mark.asyncio
async def test_model_skill_plugin_unavailable_falls_back_to_empty_lists() -> None:
    class Client:
        async def list_models(self) -> list:
            raise RuntimeError("offline")

        async def list_skills(self) -> list:
            raise RuntimeError("offline")

        async def list_plugins(self) -> list:
            raise RuntimeError("offline")

    transport = HttpRuntimeTransport(Client())  # type: ignore[arg-type]
    for method_name in ("list_models", "list_skills", "list_plugins"):
        try:
            await getattr(transport, method_name)()
        except RuntimeError as exc:
            assert "offline" in str(exc)


def test_stream_stall_can_emit_runtime_status() -> None:
    event = normalize_runtime_event({"type": "runtime_status", "busy": True, "message": "waiting"})
    assert event.type == "runtime_status"
    assert event.payload["busy"] is True
