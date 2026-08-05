"""Normalized runtime transport events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

RuntimeEventType = Literal[
    "text_delta",
    "tool_call",
    "tool_call_update",
    "subagent_spawn",
    "subagent_update",
    "subagent_done",
    "activity",
    "clarify",
    "approval",
    "approval_resolved",
    "message_done",
    "error",
    "heartbeat",
    "runtime_status",
]


@dataclass(frozen=True)
class RuntimeTransportEvent:
    type: RuntimeEventType
    payload: dict[str, Any] = field(default_factory=dict)
    session_id: str = ""
    source: str = "http"

    def to_legacy_payload(self) -> dict[str, Any]:
        data = dict(self.payload)
        data.setdefault("type", self.type)
        data.setdefault("event", self.type)
        if self.session_id:
            data.setdefault("session_id", self.session_id)
        return data


EVENT_ALIASES = {
    "delta": "text_delta",
    "stream_delta": "text_delta",
    "text": "text_delta",
    "done": "message_done",
    "stream_done": "message_done",
    "tool_result": "tool_call_update",
    "subagent_complete": "subagent_done",
    "status": "runtime_status",
}

KNOWN_EVENTS: set[str] = set(RuntimeEventType.__args__)  # type: ignore[attr-defined]


def normalize_runtime_event(raw: dict[str, Any], *, source: str = "http", session_id: str = "") -> RuntimeTransportEvent:
    raw_type = str(raw.get("type") or raw.get("event") or "activity")
    event_type = EVENT_ALIASES.get(raw_type, raw_type)
    payload = raw.get("payload")
    if not isinstance(payload, dict):
        payload = {key: value for key, value in raw.items() if key not in {"type", "event", "session_id"}}
    resolved_session = str(raw.get("session_id") or session_id or "")
    if event_type not in KNOWN_EVENTS:
        payload = {"message": f"Unknown runtime event: {raw_type}", "raw": raw}
        event_type = "activity"
    return RuntimeTransportEvent(
        type=event_type,  # type: ignore[arg-type]
        payload=payload,
        session_id=resolved_session,
        source=source,
    )


def normalize_gateway_event(raw: dict[str, Any], *, session_id: str = "") -> RuntimeTransportEvent:
    if raw.get("type") == "connected":
        return RuntimeTransportEvent(type="heartbeat", payload={"connected": True}, session_id=session_id, source="websocket")
    return normalize_runtime_event(raw, source="websocket", session_id=session_id)


__all__ = ["RuntimeEventType", "RuntimeTransportEvent", "normalize_gateway_event", "normalize_runtime_event"]
