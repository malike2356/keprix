"""Telegram interface adapter using slash command execution."""

from __future__ import annotations

from typing import Any

from keprix.slash.executor import build_context, execute_context
from keprix.slash.renderers import render_telegram


async def handle_telegram(*, agent_id: str, trace_id: str, **payload: Any) -> dict[str, Any]:
    text = payload.get("text", "/status")
    is_group = bool(payload.get("is_group", False))
    bot_username = payload.get("bot_username")
    if is_group and bot_username and f"@{bot_username.lower()}" not in text.lower():
        if not text.startswith("/"):
            raise ValueError("group command requires /command@BotName or mention")
    ctx = build_context(
        raw_text=text if text.startswith("/") else f"/{text}",
        user_id=payload.get("user_id", "telegram-user"),
        workspace_id=payload.get("workspace_id", "default"),
        channel="telegram",
        channel_user_id=payload.get("chat_id", "telegram-chat"),
        role=payload.get("role"),
        request_id=trace_id,
        metadata={"bot_username": bot_username, "is_group": is_group},
    )
    result = await execute_context(ctx)
    return {**render_telegram(result), "trace_id": trace_id, "agent_id": agent_id, "interface": "telegram"}
