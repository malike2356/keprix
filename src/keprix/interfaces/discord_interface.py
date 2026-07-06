"""Discord interface adapter using slash command execution."""

from __future__ import annotations

from typing import Any

from keprix.slash.executor import build_context, execute_context
from keprix.slash.renderers import render_discord


async def handle_discord(*, agent_id: str, trace_id: str, **payload: Any) -> dict[str, Any]:
    normalized = payload.get("text", "/status")
    if not normalized.startswith("/"):
        normalized = f"/{normalized.lstrip('/')}"
    if normalized.startswith("/keprix "):
        normalized = "/" + normalized[len("/keprix ") :]
    if normalized.startswith("/carina "):
        normalized = "/" + normalized[len("/carina ") :]
    ctx = build_context(
        raw_text=normalized,
        user_id=payload.get("user_id", "discord-user"),
        workspace_id=payload.get("workspace_id", "default"),
        channel="discord",
        channel_user_id=payload.get("channel_id", "discord-channel"),
        role=payload.get("role"),
        request_id=trace_id,
    )
    result = await execute_context(ctx)
    return {**render_discord(result), "trace_id": trace_id, "agent_id": agent_id, "interface": "discord"}
