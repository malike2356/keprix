"""WhatsApp interface adapter using slash command execution."""

from __future__ import annotations

from typing import Any

from keprix.slash.executor import build_context, execute_context
from keprix.slash.renderers import render_text


async def handle_whatsapp(*, agent_id: str, trace_id: str, **payload: Any) -> dict[str, Any]:
    text = payload.get("text", "/status")
    normalized = text if text.startswith("/") else f"/{text.lstrip('/')}"
    ctx = build_context(
        raw_text=normalized,
        user_id=payload.get("user_id", "whatsapp-user"),
        workspace_id=payload.get("workspace_id", "default"),
        channel="whatsapp",
        channel_user_id=payload.get("phone", payload.get("channel_user_id", "whatsapp-user")),
        role=payload.get("role"),
        request_id=trace_id,
    )
    result = await execute_context(ctx)
    rendered = render_text(result)
    return {
        "text": rendered,
        "ok": result.ok,
        "trace_id": trace_id,
        "agent_id": agent_id,
        "interface": "whatsapp",
    }
