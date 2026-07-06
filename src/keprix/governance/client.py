"""HTTP client for optional external governance providers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from keprix.governance.enrollment import GovernanceEnrollmentError, enroll_instance
from keprix.governance.event_reporter import flush_events, queue_audit_event, resume_reporting
from keprix.governance.heartbeat import run_heartbeat_if_enabled
from keprix.governance.kill_relay import clear_kill_state, get_kill_state
from keprix.governance.policy_receiver import get_policy_registry, reload_policies
from keprix.governance.store import get_governance_store
from keprix.security.vault_service import get_vault_service


class GovernanceClient:
    async def resolve_api_key(self, *, user_id: str | None = None) -> str | None:
        cfg = await get_governance_store().get_config()
        vault_id = cfg.get("api_key_vault_id")
        if not vault_id:
            return None
        owner = str(cfg.get("vault_user_id") or user_id or "admin")
        item = await get_vault_service().get_item(str(vault_id), owner, decrypt=True)
        if item is None or not item._value:
            return None
        return item._value

    async def status(self) -> dict[str, Any]:
        cfg = await get_governance_store().get_config()
        policies = await get_governance_store().list_policies(active_only=True)
        kill = get_kill_state().to_dict()
        return {
            "enabled": bool(cfg.get("enabled")),
            "connected": bool(cfg.get("enabled") and cfg.get("instance_id") and cfg.get("api_key_vault_id")),
            "provider_endpoint": cfg.get("provider_endpoint"),
            "instance_id": cfg.get("instance_id"),
            "enrolled_at": cfg.get("enrolled_at"),
            "last_heartbeat_at": cfg.get("last_heartbeat_at"),
            "last_heartbeat_ok": cfg.get("last_heartbeat_ok"),
            "reporting_paused": bool(cfg.get("reporting_paused")),
            "policies": policies,
            "policy_snapshot": get_policy_registry().snapshot(),
            "kill_state": kill,
        }

    async def connect(
        self,
        *,
        user_id: str,
        provider_endpoint: str,
        api_key: str,
    ) -> dict[str, Any]:
        vault = get_vault_service()
        cfg = await get_governance_store().get_config()
        old_vault_id = cfg.get("api_key_vault_id")
        if old_vault_id:
            await vault.delete_item(str(old_vault_id), user_id)
        item = await vault.create_item(
            user_id,
            label="Governance API key",
            value=api_key,
            category="api_key",
            tags=["governance"],
        )
        instance_id = await enroll_instance(provider_endpoint=provider_endpoint, api_key=api_key)
        now = datetime.now(timezone.utc).isoformat()
        saved = await get_governance_store().save_config(
            {
                "enabled": True,
                "provider_endpoint": provider_endpoint.rstrip("/"),
                "api_key_vault_id": item.id,
                "vault_user_id": user_id,
                "instance_id": instance_id,
                "enrolled_at": now,
                "reporting_paused": False,
                "consecutive_failures": 0,
            }
        )
        await resume_reporting()
        await reload_policies()
        return saved

    async def disconnect(self, *, user_id: str, accept_responsibility: bool) -> dict[str, Any]:
        if not accept_responsibility:
            raise ValueError("You must accept responsibility for ungoverned operation")
        cfg = await get_governance_store().get_config()
        vault_id = cfg.get("api_key_vault_id")
        if vault_id:
            await get_vault_service().delete_item(str(vault_id), user_id)
        saved = await get_governance_store().save_config(
            {
                "enabled": False,
                "api_key_vault_id": None,
                "vault_user_id": None,
                "instance_id": None,
                "enrolled_at": None,
                "last_heartbeat_at": None,
                "last_heartbeat_ok": None,
                "reporting_paused": False,
                "consecutive_failures": 0,
            }
        )
        clear_kill_state()
        return saved

    async def heartbeat(self, *, user_id: str) -> dict[str, Any]:
        api_key = await self.resolve_api_key(user_id=user_id)
        return await run_heartbeat_if_enabled(api_key)

    async def enqueue_event(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        await queue_audit_event(event_type, payload)
        return {"queued": True, "event_type": event_type}

    async def flush_events(self, *, user_id: str) -> dict[str, Any]:
        api_key = await self.resolve_api_key(user_id=user_id)
        return await flush_events(api_key=api_key)


_client: GovernanceClient | None = None


def get_governance_client() -> GovernanceClient:
    global _client
    if _client is None:
        _client = GovernanceClient()
    return _client
