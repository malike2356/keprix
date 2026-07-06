"""Activation routing for wake word triggers."""

from __future__ import annotations

import uuid
from typing import Any

from keprix.voice.wake import WakeWordRoutingConfig


def resolve_activation_target(
    routing: WakeWordRoutingConfig,
    *,
    node_id: str,
    active_session_id: str | None = None,
) -> dict[str, Any]:
    device_target = routing.device_targets.get(node_id)
    target = device_target or routing.default_target
    mode = str(target.get("mode", "current"))

    if mode == "active_session" and active_session_id:
        return {"mode": mode, "session_id": active_session_id, "node_id": node_id}
    if mode == "specific_node":
        return {
            "mode": mode,
            "node_id": str(target.get("node_id") or node_id),
            "session_id": target.get("session_id"),
        }
    return {"mode": "current", "node_id": node_id}


def new_voice_session_id() -> str:
    return f"voice-{uuid.uuid4().hex[:12]}"
