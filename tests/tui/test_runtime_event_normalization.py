from __future__ import annotations

from keprix.tui.runtime_transport.events import normalize_gateway_event, normalize_runtime_event


def test_runtime_event_aliases_are_normalized() -> None:
    assert normalize_runtime_event({"type": "delta", "content": "a"}).type == "text_delta"
    assert normalize_runtime_event({"type": "done"}).type == "message_done"
    assert normalize_runtime_event({"type": "tool_result"}).type == "tool_call_update"


def test_unknown_event_becomes_activity_with_raw_payload() -> None:
    event = normalize_runtime_event({"type": "new_kind", "x": 1})
    assert event.type == "activity"
    assert event.payload["raw"]["x"] == 1


def test_gateway_connected_becomes_heartbeat() -> None:
    event = normalize_gateway_event({"type": "connected"}, session_id="s1")
    assert event.type == "heartbeat"
    assert event.payload["connected"] is True
    assert event.source == "websocket"


def test_legacy_payload_roundtrip() -> None:
    event = normalize_runtime_event({"type": "runtime_status", "busy": True}, session_id="s1")
    assert event.to_legacy_payload() == {
        "busy": True,
        "event": "runtime_status",
        "type": "runtime_status",
        "session_id": "s1",
    }
