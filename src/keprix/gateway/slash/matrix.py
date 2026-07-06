"""Matrix slash command adapter."""

from __future__ import annotations

from typing import Any

from keprix.slash.executor import build_context, execute_context
from keprix.slash.renderers import render_text


async def handle_matrix_slash(
    *,
    text: str,
    user_id: str,
    workspace_id: str,
    room_id: str,
    role: str | None = None,
) -> dict[str, Any]:
    normalized = text.strip()
    if normalized.startswith("/carina "):
        normalized = "/" + normalized[len("/carina ") :]
    elif not normalized.startswith("/"):
        normalized = f"/{normalized}"
    ctx = build_context(
        raw_text=normalized,
        user_id=user_id,
        workspace_id=workspace_id,
        channel="matrix",
        channel_user_id=room_id,
        role=role,
    )
    result = await execute_context(ctx)
    return {"message": render_text(result), "ephemeral": result.ephemeral}
