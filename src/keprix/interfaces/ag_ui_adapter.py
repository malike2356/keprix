"""AG-UI protocol adapter with shared tracing."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def ag_ui_event(event_type: str, *, trace_id: str, agent_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "type": event_type,
        "trace_id": trace_id,
        "agent_id": agent_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload or {},
    }


async def handle_ag_ui(*, agent_id: str, trace_id: str, **payload: Any) -> dict[str, Any]:
    message = payload.get("message", payload.get("text", ""))
    events = [
        ag_ui_event("run_started", trace_id=trace_id, agent_id=agent_id, payload={"input": message}),
        ag_ui_event("message", trace_id=trace_id, agent_id=agent_id, payload={"role": "user", "content": message}),
    ]

    from keprix.interfaces.interface_registry import InterfaceKind, get_interface_registry

    registry = get_interface_registry()
    web_result = await registry.dispatch(
        agent_id,
        InterfaceKind.WEB_UI,
        trace_id=trace_id,
        message=message or "/status",
        user_id=payload.get("user_id", "ag-ui"),
        workspace_id=payload.get("workspace_id", "default"),
    )
    response_text = ""
    if web_result.ok:
        response_text = str(web_result.payload.get("text") or web_result.payload.get("message") or "")
    events.append(
        ag_ui_event(
            "message",
            trace_id=trace_id,
            agent_id=agent_id,
            payload={"role": "assistant", "content": response_text},
        )
    )
    events.append(ag_ui_event("run_finished", trace_id=trace_id, agent_id=agent_id, payload={"ok": web_result.ok}))
    return {"events": events, "trace_id": trace_id, "agent_id": agent_id, "interface": "ag_ui"}


def serialize_ag_ui_stream(events: list[dict[str, Any]]) -> str:
    import json

    return "\n".join(json.dumps(event) for event in events)
