"""Queue and flush Governance security events."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx

from keprix.governance.signing import sign_payload
from keprix.governance.store import get_governance_store

MAX_FAILURES = 3
BATCH_SIZE = 100


async def queue_audit_event(event_type: str, payload: dict[str, Any]) -> None:
    store = get_governance_store()
    cfg = await store.get_config()
    if not cfg.get("enabled") or cfg.get("reporting_paused"):
        return
    await store.enqueue_event(event_type, payload)


async def flush_events(*, api_key: str | None) -> dict[str, Any]:
    store = get_governance_store()
    cfg = await store.get_config()
    if not cfg.get("enabled"):
        return {"flushed": 0, "reason": "governance disabled"}
    if cfg.get("reporting_paused"):
        return {"flushed": 0, "reason": "reporting paused"}
    if not api_key or not cfg.get("provider_endpoint") or not cfg.get("instance_id"):
        return {"flushed": 0, "reason": "not configured"}

    pending = await store.list_pending_events(limit=BATCH_SIZE)
    if not pending:
        return {"flushed": 0}

    body = json.dumps(
        {
            "instance_id": cfg["instance_id"],
            "events": pending,
        }
    ).encode("utf-8")
    signature = sign_payload(api_key, body)
    url = f"{str(cfg['provider_endpoint']).rstrip('/')}/api/v1/events"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Governance-Signature": f"sha256={signature}",
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, content=body, headers=headers)
        if response.status_code < 400:
            await store.mark_events_sent([row["id"] for row in pending])
            await store.save_config({"consecutive_failures": 0})
            return {"flushed": len(pending)}
        failures = int(cfg.get("consecutive_failures") or 0) + 1
        patch: dict[str, Any] = {"consecutive_failures": failures}
        if failures >= MAX_FAILURES:
            patch["reporting_paused"] = True
        await store.save_config(patch)
        return {"flushed": 0, "status_code": response.status_code, "failures": failures}
    except Exception as exc:
        failures = int(cfg.get("consecutive_failures") or 0) + 1
        patch = {"consecutive_failures": failures}
        if failures >= MAX_FAILURES:
            patch["reporting_paused"] = True
        await store.save_config(patch)
        return {"flushed": 0, "reason": str(exc), "failures": failures}


async def resume_reporting() -> None:
    await get_governance_store().save_config({"reporting_paused": False, "consecutive_failures": 0})
