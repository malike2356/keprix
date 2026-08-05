"""integration_config agent tool."""

from __future__ import annotations

import json
from typing import Any

from tools.registry import registry


def check_integration_config_requirements() -> bool:
    return True


def integration_config_tool(
    action: str,
    integration_id: str | None = None,
    credentials: dict[str, Any] | None = None,
    session_id: str | None = None,
    webhook_id: str | None = None,
) -> str:
    from keprix.configure import integration_config_service as svc

    act = (action or "").strip().lower()
    if act == "list":
        return json.dumps(svc.list_integrations_payload(), ensure_ascii=False)

    if act == "requirements":
        if not integration_id:
            return json.dumps({"ok": False, "error": "integration_id is required"}, ensure_ascii=False)
        return json.dumps(svc.requirements_payload(integration_id), ensure_ascii=False)

    if act == "collect":
        if not integration_id:
            return json.dumps({"ok": False, "error": "integration_id is required"}, ensure_ascii=False)
        creds = {str(k): str(v) for k, v in (credentials or {}).items() if v is not None}
        result = svc.collect_and_maybe_save(integration_id, creds or None, session_id=session_id)
        # Keep signing_secret_once if present (one-time); strip other secrets
        result.pop("credentials", None)
        return json.dumps(result, ensure_ascii=False)

    if act == "configure":
        if not integration_id:
            return json.dumps({"ok": False, "error": "integration_id is required"}, ensure_ascii=False)
        creds = {str(k): str(v) for k, v in (credentials or {}).items() if v is not None}
        result = svc.configure_integration(integration_id, creds)
        result.pop("credentials", None)
        return json.dumps(result, ensure_ascii=False)

    if act == "test":
        if not integration_id:
            return json.dumps({"success": False, "message": "integration_id is required"}, ensure_ascii=False)
        return json.dumps(svc.test_integration(integration_id), ensure_ascii=False)

    if act == "remove":
        if not integration_id:
            return json.dumps({"ok": False, "error": "integration_id is required"}, ensure_ascii=False)
        return json.dumps(
            svc.remove_integration(integration_id, webhook_id=webhook_id),
            ensure_ascii=False,
        )

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


INTEGRATION_CONFIG_SCHEMA = {
    "name": "integration_config",
    "description": (
        "Configure product integrations conversationally: Notion, Trello, "
        "Google Workspace / Calendar (OAuth), and outbound webhooks. "
        "Actions: list | requirements | collect | configure | test | remove. "
        "Never dump the user into Settings-only flows. Never repeat secrets "
        "(except one-time signing_secret_once / oauth instructions)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "requirements", "collect", "configure", "test", "remove"],
            },
            "integration_id": {
                "type": "string",
                "description": "notion | trello | google_workspace | webhooks (aliases: calendar, gws, webhook).",
            },
            "credentials": {
                "type": "object",
                "additionalProperties": {"type": "string"},
            },
            "session_id": {"type": "string"},
            "webhook_id": {"type": "string", "description": "Required when removing a webhook."},
        },
        "required": ["action"],
    },
}

registry.register(
    name="integration_config",
    toolset="integrations",
    schema=INTEGRATION_CONFIG_SCHEMA,
    handler=lambda args, **kw: integration_config_tool(
        action=str(args.get("action") or ""),
        integration_id=args.get("integration_id"),
        credentials=args.get("credentials") if isinstance(args.get("credentials"), dict) else None,
        session_id=args.get("session_id"),
        webhook_id=args.get("webhook_id"),
    ),
    check_fn=check_integration_config_requirements,
    emoji="🔌",
    max_result_size_chars=50_000,
)
