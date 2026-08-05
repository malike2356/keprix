"""Periodic compliance and audit evidence push to Scout."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from keprix.governance.signing import sign_payload
from keprix.governance.store import get_governance_store
from keprix.security.scout_config import ScoutConfig

logger = logging.getLogger(__name__)

SYNC_INTERVAL = 30 * 60


class ScoutSync:
    """Pushes aggregated compliance evidence to Scout on a fixed interval."""

    def __init__(self, config: ScoutConfig) -> None:
        self._config = config
        self._last_sync_at: str | None = None

    @property
    def enabled(self) -> bool:
        return self._config.enabled and bool(self._config.api_key)

    async def sync_once(self) -> dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "skipped": True, "reason": "scout disabled"}
        payload = await self._build_payload()
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = sign_payload(self._config.api_key or "", body)
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
            "X-Governance-Signature": f"sha256={signature}",
        }
        if self._config.agent_id:
            headers["X-Agent-Id"] = self._config.agent_id
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self._config.sync_url, content=body, headers=headers)
            ok = response.status_code < 400
            self._last_sync_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            return {
                "ok": ok,
                "status_code": response.status_code,
                "synced_at": self._last_sync_at,
            }
        except Exception as exc:
            logger.warning("ScoutSync failed: %s", exc)
            return {"ok": False, "reason": str(exc)}

    async def _build_payload(self) -> dict[str, Any]:
        store = get_governance_store()
        cfg = await store.get_config()
        pending = await store.list_pending_events(limit=500)
        from keprix.security.scout_control import snapshot as control_snapshot

        return {
            "instance_id": self._config.agent_id or cfg.get("instance_id"),
            "product": self._config.product,
            "synced_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "since_last_sync": self._last_sync_at,
            "governance": {
                "enabled": bool(cfg.get("enabled")),
                "pending_event_count": len(pending),
                "policy_snapshot": __import__(
                    "keprix.governance.policy_receiver", fromlist=["get_policy_registry"]
                ).get_policy_registry().snapshot(),
            },
            "control_state": control_snapshot(),
            "audit_events": pending,
        }

    async def sync_loop(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            await self.sync_once()
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=SYNC_INTERVAL)
            except TimeoutError:
                pass


_sync: ScoutSync | None = None


def get_scout_sync() -> ScoutSync:
    global _sync
    if _sync is None:
        from keprix.security.scout_config import resolve_scout_config

        _sync = ScoutSync(resolve_scout_config())
    return _sync


def reset_scout_sync() -> None:
    global _sync
    _sync = None
