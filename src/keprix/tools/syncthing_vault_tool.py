"""Agent tool: syncthing vault bridge status / ensure."""

from __future__ import annotations

import json
from typing import Any

from keprix.sync.syncthing.client import SyncthingError
from keprix.sync.syncthing.service import ensure_vault_folder, get_status, pause_folder
from keprix.tools.registry import registry

TOOLSET = "syncthing"


def _schema() -> dict[str, Any]:
    return {
        "name": "syncthing_vault",
        "description": (
            "Obsidian vault Syncthing bridge (not GitHub agent-sync). "
            "Actions: status, ensure_folder, pause, resume. "
            "Syncthing syncs the vault only; agent-sync owns memory/skills."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["status", "ensure_folder", "pause", "resume"]},
            },
            "required": ["action"],
        },
    }


def _handle(args: dict[str, Any], **_kwargs: Any) -> str:
    action = str(args.get("action") or "status")
    try:
        if action == "status":
            return json.dumps(get_status())
        if action == "ensure_folder":
            return json.dumps(ensure_vault_folder())
        if action == "pause":
            return json.dumps(pause_folder(True))
        if action == "resume":
            return json.dumps(pause_folder(False))
        return json.dumps({"error": f"unknown action: {action}"})
    except SyncthingError as exc:
        return json.dumps({"error": str(exc)})


registry.register(name="syncthing_vault", toolset=TOOLSET, schema=_schema(), handler=_handle)
