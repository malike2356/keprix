"""Telegram slash command adapter."""

from __future__ import annotations

from typing import Any

from keprix.slash.executor import build_context, execute_context
from keprix.slash.renderers import render_telegram


async def handle_telegram_slash(
    *,
    text: str,
    user_id: str,
    workspace_id: str,
    chat_id: str,
    is_group: bool = False,
    bot_username: str | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    if is_group and bot_username and f"@{bot_username.lower()}" not in text.lower():
        if not text.startswith("/"):
            raise ValueError("group command requires /command@BotName or mention")
    ctx = build_context(
        raw_text=text if text.startswith("/") else f"/{text}",
        user_id=user_id,
        workspace_id=workspace_id,
        channel="telegram",
        channel_user_id=chat_id,
        role=role,
        metadata={"bot_username": bot_username, "is_group": is_group},
    )
    result = await execute_context(ctx)
    return render_telegram(result)


def telegram_bot_commands() -> list[dict[str, str]]:
    from keprix.slash.registry import get_slash_registry

    commands = []
    for command in get_slash_registry().list_for_role("viewer"):
        name = command.name.split(".")[0]
        if len(name) > 32:
            continue
        commands.append({"command": name, "description": command.description[:256]})
    return commands
