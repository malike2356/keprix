"""Tests for subagent NDJSON stream events (Prompt 206)."""

from __future__ import annotations

from keprix.interfaces.web_ui_stream_events import GatewayStreamEvent, map_gateway_event_to_ndjson


def test_map_subagent_spawn_event() -> None:
    payload = map_gateway_event_to_ndjson(
        GatewayStreamEvent(
            "subagent_spawn",
            {"subagent_id": "sa-1", "label": "coder-1", "goal": "refactor auth/"},
        )
    )
    assert payload["event"] == "subagent_spawn"
    assert payload["subagent_id"] == "sa-1"
    assert payload["label"] == "coder-1"


def test_map_subagent_done_event() -> None:
    payload = map_gateway_event_to_ndjson(
        GatewayStreamEvent(
            "subagent_done",
            {
                "subagent_id": "sa-1",
                "label": "coder-1",
                "status": "done",
                "cost_hint": "$0.02",
            },
        )
    )
    assert payload["event"] == "subagent_done"
    assert payload["cost_hint"] == "$0.02"


def test_map_activity_event() -> None:
    payload = map_gateway_event_to_ndjson(
        GatewayStreamEvent("activity", {"message": "Indexing memory..."})
    )
    assert payload == {"event": "activity", "message": "Indexing memory..."}
