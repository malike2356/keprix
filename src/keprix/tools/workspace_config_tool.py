"""workspace_config agent tool."""

from __future__ import annotations

import json
from typing import Any

from tools.registry import registry


def check_workspace_config_requirements() -> bool:
    return True


def workspace_config_tool(
    action: str,
    settings: dict[str, Any] | None = None,
    field: str | None = None,
    credentials: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> str:
    from keprix.configure import workspace_config_service as svc

    act = (action or "").strip().lower()
    if act == "list":
        return json.dumps(svc.list_workspace_payload(), ensure_ascii=False)

    if act == "requirements":
        return json.dumps(svc.requirements_payload(field), ensure_ascii=False)

    if act == "collect":
        creds = credentials or settings
        result = svc.collect_workspace(creds, session_id=session_id or "default", field=field)
        return json.dumps(result, ensure_ascii=False)

    if act == "configure":
        payload = settings or credentials or {}
        if field and credentials and len(credentials) == 1:
            payload = credentials
        elif field and credentials and field in (credentials or {}):
            payload = {field: credentials[field]}
        return json.dumps(svc.configure_workspace(payload), ensure_ascii=False)

    return json.dumps(
        {
            "ok": False,
            "error": f"Unknown action '{action}'. Use list | requirements | collect | configure.",
        },
        ensure_ascii=False,
    )


WORKSPACE_CONFIG_SCHEMA = {
    "name": "workspace_config",
    "description": (
        "Manage durable workspace preferences: timezone, language, instance name/URL, "
        "quiet hours. Actions: list | requirements | collect | configure. "
        "Never send the user hunting through Settings for these."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "requirements", "collect", "configure"],
            },
            "field": {"type": "string"},
            "settings": {"type": "object", "additionalProperties": True},
            "credentials": {"type": "object", "additionalProperties": True},
            "session_id": {"type": "string"},
        },
        "required": ["action"],
    },
}

registry.register(
    name="workspace_config",
    toolset="workspace",
    schema=WORKSPACE_CONFIG_SCHEMA,
    handler=lambda args, **kw: workspace_config_tool(
        action=str(args.get("action") or ""),
        settings=args.get("settings") if isinstance(args.get("settings"), dict) else None,
        field=args.get("field"),
        credentials=args.get("credentials") if isinstance(args.get("credentials"), dict) else None,
        session_id=args.get("session_id"),
    ),
    check_fn=check_workspace_config_requirements,
    emoji="⚙️",
    max_result_size_chars=50_000,
)
