"""Event triggers for control center automations."""

from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.control_center.run_queue import enqueue_run
from keprix.control_center.store import get_control_center_store
from keprix.governance.signing import verify_signature
from keprix.security.vault_service import get_vault_service

SUPPORTED_TRIGGERS = {
    "schedule",
    "webhook",
    "github_issue",
    "pull_request",
    "file_watch",
    "email",
    "channel_message",
    "manual",
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_webhook_automation(
    *,
    name: str,
    playbook_id: str,
    owner: str,
    server_id: str | None = None,
) -> dict[str, Any]:
    store = get_control_center_store()
    secret = secrets.token_hex(32)
    vault = get_vault_service()
    item = await vault.create_item(
        user_id=owner,
        label=f"control-center-webhook:{name}",
        category="api_key",
        value=secret,
        tags=["control-center", "webhook"],
    )
    automation = {
        "id": str(uuid.uuid4()),
        "name": name,
        "trigger_type": "webhook",
        "playbook_id": playbook_id,
        "server_id": server_id,
        "config": {},
        "enabled": True,
        "last_run_at": None,
        "created_at": _utcnow(),
        "webhook_secret_vault_id": item.id,
    }
    store.save_automation(automation)
    store.set_webhook_secret_ref(automation["id"], item.id)
    store.append_activity(
        {
            "type": "automation_created",
            "message": f"Webhook automation {name}",
            "automation_id": automation["id"],
        }
    )
    return {
        "automation": {key: value for key, value in automation.items() if key != "webhook_secret_vault_id"},
        "webhook_path": f"/api/control-center/webhooks/{automation['id']}",
    }


async def resolve_webhook_secret(automation_id: str, owner: str) -> str | None:
    store = get_control_center_store()
    automation = store.get_automation(automation_id)
    if automation is None:
        return None
    vault_id = automation.get("webhook_secret_vault_id") or store.get_webhook_secret_ref(automation_id)
    if not vault_id:
        return None
    item = await get_vault_service().get_item(vault_id, owner, decrypt=True)
    if item is None:
        return None
    return getattr(item, "_value", None) or getattr(item, "value", None)


async def trigger_from_webhook(
    automation_id: str,
    *,
    body: bytes,
    signature_header: str | None,
    owner: str,
) -> dict[str, Any]:
    store = get_control_center_store()
    automation = store.get_automation(automation_id)
    if automation is None or automation.get("trigger_type") != "webhook":
        raise ValueError("Webhook automation not found")
    if not automation.get("enabled", True):
        raise ValueError("Automation disabled")
    secret = await resolve_webhook_secret(automation_id, owner)
    if not secret or not verify_signature(secret, body, signature_header):
        raise PermissionError("Invalid webhook signature")
    payload = json.loads(body.decode("utf-8")) if body else {}
    run = enqueue_run(
        automation_id=automation_id,
        payload={
            "playbook_id": automation.get("playbook_id"),
            "server_id": automation.get("server_id"),
            "trigger": "webhook",
            "event": payload,
        },
    )
    automation["last_run_at"] = _utcnow()
    store.save_automation(automation)
    return run


def trigger_manual(automation_id: str) -> dict[str, Any] | None:
    store = get_control_center_store()
    automation = store.get_automation(automation_id)
    if automation is None:
        return None
    run = enqueue_run(
        automation_id=automation_id,
        payload={
            "playbook_id": automation.get("playbook_id"),
            "server_id": automation.get("server_id"),
            "trigger": "manual",
        },
    )
    automation["last_run_at"] = _utcnow()
    store.save_automation(automation)
    return run
