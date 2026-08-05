"""channel_config agent tool: conversational messaging/mail setup."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from tools.registry import registry


def check_channel_config_requirements() -> bool:
    return True


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


def channel_config_tool(
    action: str,
    channel_id: str | None = None,
    credentials: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> str:
    """Manage messaging and mail channel connections."""
    from keprix.channels import channel_config_service as svc

    act = (action or "").strip().lower()
    if act == "list":
        return json.dumps(svc.list_channels_payload(), ensure_ascii=False)

    if act == "requirements":
        if not channel_id:
            return json.dumps({"ok": False, "error": "channel_id is required"}, ensure_ascii=False)
        return json.dumps(svc.requirements_payload(channel_id), ensure_ascii=False)

    if act == "collect":
        if not channel_id:
            return json.dumps({"ok": False, "error": "channel_id is required"}, ensure_ascii=False)
        creds = {str(k): str(v) for k, v in (credentials or {}).items() if v is not None}
        result = _run_async(
            svc.collect_and_maybe_save(channel_id, creds or None, session_id=session_id)
        )
        result.pop("credentials", None)
        return json.dumps(result, ensure_ascii=False)

    if act == "configure":
        if not channel_id:
            return json.dumps({"ok": False, "error": "channel_id is required"}, ensure_ascii=False)
        creds = {str(k): str(v) for k, v in (credentials or {}).items() if v is not None}
        result = _run_async(svc.configure_and_test(channel_id, creds))
        result.pop("credentials", None)
        return json.dumps(result, ensure_ascii=False)

    if act == "test":
        if not channel_id:
            return json.dumps({"success": False, "message": "channel_id is required"}, ensure_ascii=False)
        return json.dumps(_run_async(svc.test_channel_payload(channel_id)), ensure_ascii=False)

    if act == "remove":
        if not channel_id:
            return json.dumps({"ok": False, "error": "channel_id is required"}, ensure_ascii=False)
        return json.dumps(svc.remove_channel_payload(channel_id), ensure_ascii=False)

    return json.dumps(
        {
            "ok": False,
            "error": (
                f"Unknown action '{action}'. "
                "Use list | requirements | collect | configure | test | remove."
            ),
        },
        ensure_ascii=False,
    )


CHANNEL_CONFIG_SCHEMA = {
    "name": "channel_config",
    "description": (
        "Manage messaging and mail channel connections. "
        "Actions: list | requirements | collect | configure | test | remove. "
        "Prefer collect for BotFather-style one-field-at-a-time setup: call collect "
        "with channel_id to get next_field, then call collect again with that single "
        "field in credentials until complete (auto-saves and tests). "
        "Use configure only when all credentials are already known. "
        "Never tell the user to dig through dashboard pages for these tasks. "
        "Never repeat secret values in your reply."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "requirements", "collect", "configure", "test", "remove"],
                "description": "Operation to perform.",
            },
            "channel_id": {
                "type": "string",
                "description": (
                    "Channel id or alias (telegram, tg, smtp, mail, slack, discord, "
                    "whatsapp, wa, signal, matrix, sms, teams, ...)."
                ),
            },
            "credentials": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": (
                    "Field keys from the channel requirements registry. "
                    "For collect, pass one answered field at a time."
                ),
            },
            "session_id": {
                "type": "string",
                "description": "Optional setup session id (defaults to 'default').",
            },
        },
        "required": ["action"],
    },
}

registry.register(
    name="channel_config",
    toolset="channels",
    schema=CHANNEL_CONFIG_SCHEMA,
    handler=lambda args, **kw: channel_config_tool(
        action=str(args.get("action") or ""),
        channel_id=args.get("channel_id"),
        credentials=args.get("credentials") if isinstance(args.get("credentials"), dict) else None,
        session_id=args.get("session_id"),
    ),
    check_fn=check_channel_config_requirements,
    emoji="📡",
    max_result_size_chars=50_000,
)
