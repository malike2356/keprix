"""Web UI NDJSON stream event contract (Prompt 142).

Distinct from ``gateway.stream_events.StreamEvent`` (agent-to-gateway transport).
These events are mapped directly to workspace chat NDJSON blocks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

GatewayStreamEventName = Literal[
    "text_delta",
    "text_done",
    "tool_call",
    "tool_call_update",
    "mutation",
    "error",
    "done",
    "tool_not_found",
]


@dataclass(frozen=True)
class GatewayStreamEvent:
    event: GatewayStreamEventName
    payload: dict[str, Any] = field(default_factory=dict)


def map_gateway_event_to_ndjson(event: GatewayStreamEvent) -> dict[str, Any]:
    """Map a gateway stream event to conversation API NDJSON shape."""
    name = event.event
    payload = event.payload
    if name == "text_delta":
        return {"event": "text_delta", "content": str(payload.get("content") or "")}
    if name == "text_done":
        return {"event": "text_done"}
    if name == "tool_call":
        return {
            "event": "tool_call",
            "name": payload.get("name"),
            "input": payload.get("input") or {},
            "status": payload.get("status") or "running",
        }
    if name == "tool_call_update":
        return {
            "event": "tool_call_update",
            "name": payload.get("name"),
            "output": payload.get("output"),
            "status": payload.get("status") or "done",
        }
    if name == "mutation":
        return {
            "event": "mutation",
            "id": payload.get("id"),
            "toolName": payload.get("toolName"),
            "approach": payload.get("approach"),
            "code": payload.get("code"),
            "skillYaml": payload.get("skillYaml"),
            "sandboxResult": payload.get("sandboxResult"),
            "sandboxExitCode": payload.get("sandboxExitCode", 0),
            "sandboxStderr": payload.get("sandboxStderr", ""),
            "status": payload.get("status") or "pending",
        }
    if name == "error":
        return {"event": "error", "message": str(payload.get("message") or "")}
    if name in {"done", "tool_not_found"}:
        return {"event": name, **{k: v for k, v in payload.items() if k != "event"}}
    return {"event": name, **payload}


def ndjson_chat_event_to_gateway(event: dict[str, Any]) -> GatewayStreamEvent | None:
    """Convert legacy chat mutation bridge events into gateway stream events."""
    kind = str(event.get("event") or "")
    if not kind:
        return None
    if kind == "text_delta":
        return GatewayStreamEvent("text_delta", {"content": event.get("content") or ""})
    if kind == "text_done":
        return GatewayStreamEvent("text_done", {})
    if kind == "mutation":
        return GatewayStreamEvent(
            "mutation",
            {
                "id": event.get("id"),
                "toolName": event.get("toolName"),
                "approach": event.get("approach"),
                "code": event.get("code"),
                "skillYaml": event.get("skillYaml"),
                "sandboxResult": event.get("sandboxResult"),
                "sandboxExitCode": event.get("sandboxExitCode", 0),
                "sandboxStderr": event.get("sandboxStderr", ""),
                "status": event.get("status") or "pending",
            },
        )
    return GatewayStreamEvent(kind, dict(event))
