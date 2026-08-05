"""HTTP command.dispatch handler for the Textual TUI."""

from __future__ import annotations

import asyncio
import inspect
from typing import Any

PENDING_INPUT_COMMANDS = frozenset({"retry", "queue", "q", "steer", "plan", "goal", "undo"})


def should_fallthrough_to_dispatch(command: str) -> bool:
    name = (command.split()[0] if command else "").lstrip("/").lower()
    if name in PENDING_INPUT_COMMANDS:
        return True
    try:
        from agent.skill_commands import resolve_skill_command_key

        if resolve_skill_command_key(name) is not None:
            return True
    except Exception:
        pass
    return False


def _last_user_message(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            text = content.strip()
            if text:
                return text
        elif isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("content") or ""))
            text = "\n".join(part for part in parts if part).strip()
            if text:
                return text
    return ""


async def dispatch_command(
    *,
    name: str,
    arg: str,
    session_id: str,
    messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    cleaned = (name or "").lstrip("/").lower()
    argument = (arg or "").strip()

    if cleaned in {"queue", "q"}:
        if not argument:
            return {"ok": False, "error": "queue requires a message argument", "code": 4004}
        return {"ok": True, "type": "send", "message": argument}

    if cleaned == "steer" and argument:
        return {"ok": True, "type": "send", "message": argument}

    if cleaned == "retry":
        last = _last_user_message(list(messages or []))
        if not last:
            return {"ok": False, "error": "No previous user message to retry", "code": 4004}
        return {"ok": True, "type": "send", "message": last}

    try:
        from agent.skill_commands import (
            build_skill_invocation_message,
            get_skill_commands,
            resolve_skill_command_key,
        )

        skill_key = resolve_skill_command_key(cleaned)
        if skill_key is not None:
            message = build_skill_invocation_message(skill_key, argument)
            if not message:
                return {
                    "ok": True,
                    "type": "exec",
                    "output": f"Skill /{cleaned} could not be loaded.",
                }
            skill_cmds = get_skill_commands()
            skill_name = str(skill_cmds.get(skill_key, {}).get("name") or cleaned)
            return {"ok": True, "type": "skill", "name": skill_name, "message": message}
    except Exception as exc:
        return {"ok": True, "type": "exec", "output": f"Skill dispatch failed: {exc}"}

    try:
        from keprix_cli.plugins import get_plugin_command_handler

        handler = get_plugin_command_handler(cleaned)
        if handler is not None:
            result = handler(argument)
            if inspect.isawaitable(result):
                result = await result
            return {"ok": True, "type": "plugin", "output": str(result)}
    except Exception as exc:
        return {"ok": True, "type": "exec", "output": f"Plugin command error: {exc}"}

    try:
        from keprix_cli.commands import resolve_command

        command = resolve_command(cleaned)
        if command is not None and command.name != cleaned:
            return {"ok": True, "type": "alias", "target": command.name}
    except Exception:
        pass

    return {
        "ok": False,
        "error": f"Unknown command /{cleaned}. Try /help.",
        "code": 4040,
    }
