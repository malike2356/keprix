"""Discord slash command adapter."""

from __future__ import annotations

from typing import Any

from keprix.slash.executor import build_context, execute_context
from keprix.slash.renderers import render_discord


async def handle_discord_slash(
    *,
    text: str,
    user_id: str,
    workspace_id: str,
    channel_id: str,
    role: str | None = None,
) -> dict[str, Any]:
    normalized = text if text.startswith("/") else f"/{text.lstrip('/')}"
    if normalized.startswith("/keprix "):
        normalized = "/" + normalized[len("/keprix ") :]
    if normalized.startswith("/carina "):
        normalized = "/" + normalized[len("/carina ") :]
    ctx = build_context(
        raw_text=normalized,
        user_id=user_id,
        workspace_id=workspace_id,
        channel="discord",
        channel_user_id=channel_id,
        role=role,
    )
    result = await execute_context(ctx)
    return render_discord(result)


def discord_application_commands() -> list[dict[str, Any]]:
    from keprix.slash.registry import get_slash_registry

    return [
        {
            "name": "keprix",
            "description": "Keprix slash commands",
            "options": [
                {
                    "name": command.name.replace(".", "_"),
                    "description": command.description[:100],
                    "type": 3,
                }
                for command in get_slash_registry().list_for_role("viewer")[:20]
            ],
        }
    ]
