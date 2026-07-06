"""WebChat slash command adapter."""

from __future__ import annotations

from typing import Any

from keprix.slash.executor import build_context, execute_context
from keprix.slash.renderers import render_webchat


async def handle_webchat_slash(
    *,
    text: str,
    user_id: str,
    workspace_id: str,
    session_id: str,
    role: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ctx = build_context(
        raw_text=text if text.startswith("/") else f"/{text}",
        user_id=user_id,
        workspace_id=workspace_id,
        channel="webchat",
        channel_user_id=session_id,
        role=role,
        metadata=metadata,
    )
    result = await execute_context(ctx)
    return render_webchat(result)
