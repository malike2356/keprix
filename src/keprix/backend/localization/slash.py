"""Slash command parsing and execution for localization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from keprix.backend.localization.config import LocalizationSettings
from keprix.backend.localization.preferences import get_preference_service


@dataclass
class LanguageSlashResult:
    ok: bool
    message: str
    payload: dict[str, Any] | None = None


def parse_language_slash(args: list[str]) -> tuple[str, list[str]]:
    if not args:
        return "show", []
    action = args[0].lower()
    rest = args[1:]
    if action == "set" and rest:
        return "set", rest
    if action == "voice":
        return "voice", rest
    if action == "bilingual":
        return "bilingual", rest
    if action == "reset":
        return "reset", rest
    return "show", args


async def execute_language_slash(
    *,
    workspace_id: str,
    user_id: str,
    args: list[str],
) -> LanguageSlashResult:
    action, rest = parse_language_slash(args)
    prefs = get_preference_service()
    settings = LocalizationSettings.from_env(workspace_id)

    if action == "show":
        current = await prefs.get(workspace_id, user_id, settings)
        message = (
            f"Language preferences for {user_id}:\n"
            f"- input: {current.get('preferred_input_language') or 'auto'}\n"
            f"- output: {current.get('preferred_output_language')}\n"
            f"- voice: {'on' if current.get('voice_output_enabled') else 'off'}\n"
            f"- bilingual: {'on' if current.get('bilingual_replies') else 'off'}"
        )
        return LanguageSlashResult(ok=True, message=message, payload=current)

    if action == "set" and rest:
        code = rest[0]
        updated = await prefs.update(
            workspace_id,
            user_id,
            {"preferred_output_language": code, "preferred_input_language": code},
        )
        return LanguageSlashResult(
            ok=True,
            message=f"Output language set to {code}",
            payload=updated,
        )

    if action == "voice":
        enabled = not rest or rest[0].lower() in {"on", "true", "1", "enable"}
        updated = await prefs.update(workspace_id, user_id, {"voice_output_enabled": enabled})
        state = "enabled" if enabled else "disabled"
        return LanguageSlashResult(ok=True, message=f"Voice output {state}", payload=updated)

    if action == "bilingual":
        enabled = not rest or rest[0].lower() in {"on", "true", "1", "enable"}
        updated = await prefs.update(workspace_id, user_id, {"bilingual_replies": enabled})
        state = "enabled" if enabled else "disabled"
        return LanguageSlashResult(ok=True, message=f"Bilingual replies {state}", payload=updated)

    if action == "reset":
        updated = await prefs.reset(workspace_id, user_id)
        return LanguageSlashResult(ok=True, message="Language preferences reset", payload=updated)

    return LanguageSlashResult(
        ok=False,
        message="Usage: /language [set <code>|voice on|bilingual on|reset]",
    )
