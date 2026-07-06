"""Agent server registry with vault-backed tokens."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.control_center.path_policy import validate_workspace_root
from keprix.control_center.store import get_control_center_store
from keprix.security.validation import InputValidator, ValidationError
from keprix.security.vault_service import get_vault_service

_validator = InputValidator()
DESTRUCTIVE_CAPABILITIES = {"shell", "delete", "deploy", "browser_purchase"}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


async def register_server(
    *,
    name: str,
    url: str,
    owner: str,
    workspace_root: str,
    token: str | None = None,
    capabilities: list[str] | None = None,
    sandbox_status: str = "enabled",
) -> dict[str, Any]:
    store = get_control_center_store()
    cleaned_name = _validator.validate_string(name, "name", max_length=120)
    cleaned_url = _validator.validate_url(url, "url")
    cleaned_root = validate_workspace_root(workspace_root)
    caps = list(capabilities or ["coding", "research", "playbook"])

    token_vault_id: str | None = None
    if token:
        vault = get_vault_service()
        item = await vault.create_item(
            user_id=owner,
            label=f"control-center:{cleaned_name}",
            category="api_key",
            value=token,
            tags=["control-center", "agent-server"],
        )
        token_vault_id = item.id

    server = {
        "id": str(uuid.uuid4()),
        "name": cleaned_name,
        "url": cleaned_url,
        "owner": owner,
        "workspace_root": cleaned_root,
        "capabilities": caps,
        "sandbox_status": sandbox_status,
        "health_status": "unknown",
        "last_heartbeat": None,
        "token_vault_id": token_vault_id,
        "registered_at": _utcnow(),
    }
    store.save_server(server)
    store.append_activity(
        {
            "type": "server_registered",
            "message": f"Registered agent server {cleaned_name}",
            "server_id": server["id"],
        }
    )
    return public_server(server)


def public_server(server: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": server["id"],
        "name": server["name"],
        "url": server["url"],
        "owner": server["owner"],
        "workspace_root": server["workspace_root"],
        "capabilities": list(server.get("capabilities") or []),
        "sandbox_status": server.get("sandbox_status", "enabled"),
        "health_status": server.get("health_status", "unknown"),
        "last_heartbeat": server.get("last_heartbeat"),
        "has_token": bool(server.get("token_vault_id")),
        "registered_at": server.get("registered_at"),
    }


def list_servers() -> list[dict[str, Any]]:
    return [public_server(server) for server in get_control_center_store().list_servers()]


def get_server(server_id: str) -> dict[str, Any] | None:
    server = get_control_center_store().get_server(server_id)
    if server is None:
        return None
    return public_server(server)


async def resolve_server_token(server_id: str, owner: str) -> str | None:
    server = get_control_center_store().get_server(server_id)
    if server is None or not server.get("token_vault_id"):
        return None
    vault = get_vault_service()
    item = await vault.get_item(server["token_vault_id"], owner, decrypt=True)
    if item is None:
        return None
    return getattr(item, "_value", None) or getattr(item, "value", None)


def record_heartbeat(server_id: str, *, health_status: str = "healthy") -> dict[str, Any] | None:
    store = get_control_center_store()
    server = store.get_server(server_id)
    if server is None:
        return None
    server["health_status"] = health_status
    server["last_heartbeat"] = _utcnow()
    store.save_server(server)
    return public_server(server)


def requires_approval(capabilities: list[str], task_type: str) -> bool:
    if task_type in {"coding", "browser"} and any(cap in DESTRUCTIVE_CAPABILITIES for cap in capabilities):
        return True
    return task_type in {"coding", "browser", "analytics"}
