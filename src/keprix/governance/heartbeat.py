"""Signed Governance heartbeat."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from keprix.config.constants import PRODUCT_VERSION
from keprix.governance.signing import sign_payload
from keprix.governance.store import get_governance_store


_STARTED_AT = time.time()


def _build_payload(instance_id: str) -> dict[str, Any]:
    return {
        "instance_id": instance_id,
        "version": PRODUCT_VERSION,
        "uptime_seconds": int(time.time() - _STARTED_AT),
        "provider_count": 4,
        "active_agent_count": 0,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


async def send_heartbeat(*, provider_endpoint: str, api_key: str, instance_id: str) -> dict[str, Any]:
    payload = _build_payload(instance_id)
    body = json.dumps(payload).encode("utf-8")
    signature = sign_payload(api_key, body)
    url = f"{provider_endpoint.rstrip('/')}/api/v1/heartbeat"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Governance-Signature": f"sha256={signature}",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, content=body, headers=headers)
    ok = response.status_code < 400
    store = get_governance_store()
    await store.save_config(
        {
            "last_heartbeat_at": datetime.now(timezone.utc).isoformat(),
            "last_heartbeat_ok": ok,
            "consecutive_failures": 0 if ok else (int((await store.get_config()).get("consecutive_failures") or 0) + 1),
        }
    )
    return {"ok": ok, "status_code": response.status_code}


async def run_heartbeat_if_enabled(api_key: str | None) -> dict[str, Any]:
    store = get_governance_store()
    cfg = await store.get_config()
    if not cfg.get("enabled"):
        return {"ok": False, "skipped": True, "reason": "governance disabled"}
    if not cfg.get("instance_id") or not cfg.get("provider_endpoint"):
        return {"ok": False, "skipped": True, "reason": "not enrolled"}
    if not api_key:
        return {"ok": False, "skipped": True, "reason": "missing api key"}
    try:
        return await send_heartbeat(
            provider_endpoint=str(cfg["provider_endpoint"]),
            api_key=api_key,
            instance_id=str(cfg["instance_id"]),
        )
    except Exception as exc:
        failures = int(cfg.get("consecutive_failures") or 0) + 1
        await store.save_config(
            {
                "last_heartbeat_at": datetime.now(timezone.utc).isoformat(),
                "last_heartbeat_ok": False,
                "consecutive_failures": failures,
            }
        )
        return {"ok": False, "reason": str(exc)}
