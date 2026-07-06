"""Event trigger tests (Prompt 61)."""

from __future__ import annotations

import json

import pytest

from keprix.control_center.event_triggers import create_webhook_automation, trigger_from_webhook
from keprix.control_center.store import ControlCenterStore, reset_control_center_store
from keprix.governance.signing import sign_payload
from keprix.security.vault_service import get_vault_service, reset_vault_service


@pytest.fixture
def store(tmp_path):
    reset_vault_service()
    reset_control_center_store(ControlCenterStore(base_dir=tmp_path / "control_center"))
    yield
    reset_control_center_store(None)
    reset_vault_service()


@pytest.mark.asyncio
async def test_webhook_trigger_requires_valid_signature(store):
    created = await create_webhook_automation(
        name="deploy-hook",
        playbook_id="starter-team",
        owner="admin",
    )
    automation_id = created["automation"]["id"]
    body = json.dumps({"event": "push"}).encode("utf-8")

    with pytest.raises(PermissionError):
        await trigger_from_webhook(automation_id, body=body, signature_header=None, owner="admin")

    secret_item = await get_vault_service().list_items("admin")
    secret = None
    for item in secret_item:
        full = await get_vault_service().get_item(item.id, "admin", decrypt=True)
        if full and full.label.startswith("control-center-webhook:"):
            secret = full._value
            break
    assert secret
    signature = sign_payload(secret, body)
    run = await trigger_from_webhook(
        automation_id,
        body=body,
        signature_header=f"sha256={signature}",
        owner="admin",
    )
    assert run["status"] == "queued"
    assert run["payload"]["trigger"] == "webhook"
