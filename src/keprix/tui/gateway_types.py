"""Typed gateway protocol messages for the TUI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

GatewayMessageType = Literal[
    "connected",
    "stream_delta",
    "stream_done",
    "tool_call",
    "tool_result",
    "approval_request",
    "slash_result",
    "error",
    "session_resumed",
]


@dataclass(frozen=True)
class GatewayMessage:
    type: GatewayMessageType
    session_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


def parse_gateway_message(raw: dict[str, Any]) -> GatewayMessage:
    msg_type = str(raw.get("type") or "error")
    known = GatewayMessageType.__args__  # type: ignore[attr-defined]
    if msg_type not in known:
        msg_type = "error"
        payload = {"error": "unknown gateway message", "raw": raw}
    else:
        payload = raw.get("payload")
        if not isinstance(payload, dict):
            payload = {k: v for k, v in raw.items() if k not in {"type", "session_id"}}
    session_id = raw.get("session_id")
    return GatewayMessage(type=msg_type, session_id=str(session_id) if session_id else None, payload=payload)


def serialize_gateway_message(message: GatewayMessage) -> dict[str, Any]:
    data: dict[str, Any] = {"type": message.type, "payload": dict(message.payload)}
    if message.session_id:
        data["session_id"] = message.session_id
    return data

