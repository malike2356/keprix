"""Slash command CLI."""

from __future__ import annotations

import asyncio
import json
import sys

from keprix.slash.executor import build_context, execute_context
from keprix.slash.registry import get_slash_registry


def cmd_slash_list(_args) -> int:
    commands = get_slash_registry().list_for_role("admin")
    for command in commands:
        print(f"/{command.name:20} {command.min_role:8} {command.description}")
    return 0


def cmd_slash_run(args) -> int:
    text = args.command
    if not text.startswith("/"):
        text = f"/{text}"

    async def _run() -> None:
        ctx = build_context(
            raw_text=text,
            user_id="cli",
            workspace_id="default",
            channel="cli",
            channel_user_id="cli",
            role="admin",
        )
        result = await execute_context(ctx)
        print(result.message)
        if result.requires_confirmation and result.confirmation_token:
            print(f"confirmation_token={result.confirmation_token}")
        if result.data:
            print(json.dumps(result.data, indent=2))

    try:
        asyncio.run(_run())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0
