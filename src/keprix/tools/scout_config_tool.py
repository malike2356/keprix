"""scout_config agent tool: conversational Scout pair / unpair."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from tools.registry import registry


def check_scout_config_requirements() -> bool:
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


def scout_config_tool(
    action: str,
    credentials: dict[str, Any] | None = None,
    session_id: str | None = None,
    accept_responsibility: bool = False,
) -> str:
    from keprix.configure import scout_config_service as svc

    act = (action or "").strip().lower()
    if act in {"list", "status"}:
        return json.dumps(_run_async(svc.scout_status_payload()), ensure_ascii=False)

    if act == "requirements":
        return json.dumps(svc.scout_requirements_payload(), ensure_ascii=False)

    if act == "collect":
        creds = {str(k): str(v) for k, v in (credentials or {}).items() if v is not None}
        result = _run_async(
            svc.scout_collect(creds or None, session_id=session_id or "default")
        )
        result.pop("credentials", None)
        if isinstance(result.get("config"), dict):
            result["config"] = {
                k: v
                for k, v in result["config"].items()
                if "key" not in str(k).lower() and "token" not in str(k).lower()
            }
        return json.dumps(result, ensure_ascii=False)

    if act in {"configure", "connect", "pair"}:
        creds = {str(k): str(v) for k, v in (credentials or {}).items() if v is not None}
        result = _run_async(svc.scout_connect(creds))
        result.pop("credentials", None)
        return json.dumps(result, ensure_ascii=False)

    if act in {"remove", "disconnect", "unpair"}:
        result = _run_async(
            svc.scout_disconnect(accept_responsibility=bool(accept_responsibility))
        )
        return json.dumps(result, ensure_ascii=False)

    if act == "test":
        return json.dumps(_run_async(svc.scout_status_payload()), ensure_ascii=False)

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


SCOUT_CONFIG_SCHEMA = {
    "name": "scout_config",
    "description": (
        "Pair or unpair Labyrinth Scout governance. "
        "Actions: list | requirements | collect | configure | test | remove. "
        "Collect endpoint then API key one field at a time. "
        "For remove/disconnect, set accept_responsibility=true. "
        "Never send the user hunting through Settings. Never repeat the API key."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "list",
                    "requirements",
                    "collect",
                    "configure",
                    "test",
                    "remove",
                ],
            },
            "credentials": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "provider_endpoint and/or api_key.",
            },
            "session_id": {"type": "string"},
            "accept_responsibility": {
                "type": "boolean",
                "description": "Required true when disconnecting Scout.",
            },
        },
        "required": ["action"],
    },
}

registry.register(
    name="scout_config",
    toolset="scout",
    schema=SCOUT_CONFIG_SCHEMA,
    handler=lambda args, **kw: scout_config_tool(
        action=str(args.get("action") or ""),
        credentials=args.get("credentials") if isinstance(args.get("credentials"), dict) else None,
        session_id=args.get("session_id"),
        accept_responsibility=bool(args.get("accept_responsibility")),
    ),
    check_fn=check_scout_config_requirements,
    emoji="🛡️",
    max_result_size_chars=50_000,
)
