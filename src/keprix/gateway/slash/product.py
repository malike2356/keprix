"""Dispatch Keprix product slash commands through the gateway Telegram path.

Gateway built-ins and plugins win first. Product commands (playbook, research,
crew, and related) are registered in COMMAND_REGISTRY for /help and the
Telegram menu, then executed here via the shared product slash executor.
"""

from __future__ import annotations

from typing import Any


def _command_token(text: str | None) -> str:
    raw = (text or "").strip()
    if not raw.startswith("/"):
        return ""
    body = raw[1:].split(maxsplit=1)[0]
    # Telegram may send /playbook@BotName
    body = body.split("@", 1)[0]
    return body.replace("_", "-").lower()


async def dispatch_product_slash(
    *,
    text: str,
    user_id: str,
    chat_id: str,
    channel: str = "telegram",
    workspace_id: str | None = None,
    role: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    """Run a product slash command if ``text`` names a product gateway command.

    Returns the rendered message, or ``None`` when the command is not a
    product gateway command (caller should continue normal dispatch).
    """
    from keprix_cli.commands import is_product_gateway_command

    name = _command_token(text)
    if not name or not is_product_gateway_command(name):
        return None

    from keprix.slash.executor import build_context, execute_context
    from keprix.slash.renderers import render_text

    raw = text if text.startswith("/") else f"/{text}"
    ctx = build_context(
        raw_text=raw,
        user_id=str(user_id),
        workspace_id=str(workspace_id or chat_id or "default"),
        channel=channel,
        channel_user_id=str(chat_id or user_id),
        role=role,
        metadata=metadata or {},
    )
    result = await execute_context(ctx)
    return render_text(result)
