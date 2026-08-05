"""companion_config agent tool."""

from __future__ import annotations

import json
from typing import Any

from tools.registry import registry


def check_companion_config_requirements() -> bool:
    return True


def companion_config_tool(
    action: str,
    workspace_id: str | None = None,
    server_url: str | None = None,
    pairing_id: str | None = None,
    code: str | None = None,
    device_name: str | None = None,
    platform: str | None = None,
    device_id: str | None = None,
) -> str:
    from keprix.configure import companion_config_service as svc

    act = (action or "").strip().lower()
    if act == "list":
        return json.dumps(svc.list_companion_payload(workspace_id or "default"), ensure_ascii=False)

    if act == "requirements":
        return json.dumps(svc.requirements_payload(), ensure_ascii=False)

    if act in {"create", "pair", "configure"}:
        return json.dumps(
            svc.create_pairing_payload(
                workspace_id=workspace_id or "default",
                server_url=server_url,
            ),
            ensure_ascii=False,
        )

    if act == "confirm":
        if not pairing_id or not code or not device_name:
            return json.dumps(
                {
                    "ok": False,
                    "error": "confirm requires pairing_id, code, and device_name",
                },
                ensure_ascii=False,
            )
        result = svc.confirm_pairing_payload(
            pairing_id=pairing_id,
            code=code,
            device_name=device_name,
            platform=platform or "ios",
        )
        return json.dumps(result, ensure_ascii=False)

    if act == "remove":
        if not device_id:
            return json.dumps({"ok": False, "error": "device_id is required"}, ensure_ascii=False)
        return json.dumps(svc.remove_device_payload(device_id), ensure_ascii=False)

    return json.dumps(
        {
            "ok": False,
            "error": f"Unknown action '{action}'. Use list | requirements | create | confirm | remove.",
        },
        ensure_ascii=False,
    )


COMPANION_CONFIG_SCHEMA = {
    "name": "companion_config",
    "description": (
        "Pair or manage companion devices (phone/desktop). "
        "Actions: list | requirements | create | confirm | remove. "
        "create returns a short code + QR payload for the user to scan. "
        "Never speak API tokens aloud."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "requirements", "create", "confirm", "remove"],
            },
            "workspace_id": {"type": "string"},
            "server_url": {"type": "string"},
            "pairing_id": {"type": "string"},
            "code": {"type": "string"},
            "device_name": {"type": "string"},
            "platform": {"type": "string", "enum": ["ios", "android", "macos", "windows"]},
            "device_id": {"type": "string"},
        },
        "required": ["action"],
    },
}

registry.register(
    name="companion_config",
    toolset="companion",
    schema=COMPANION_CONFIG_SCHEMA,
    handler=lambda args, **kw: companion_config_tool(
        action=str(args.get("action") or ""),
        workspace_id=args.get("workspace_id"),
        server_url=args.get("server_url"),
        pairing_id=args.get("pairing_id"),
        code=args.get("code"),
        device_name=args.get("device_name"),
        platform=args.get("platform"),
        device_id=args.get("device_id"),
    ),
    check_fn=check_companion_config_requirements,
    emoji="📱",
    max_result_size_chars=80_000,
)
