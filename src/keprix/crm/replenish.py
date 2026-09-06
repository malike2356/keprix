"""Idempotent lead-list replenishment through the canonical discovery runner."""

from __future__ import annotations

import math
from typing import Any

from keprix.crm.store import CrmStore, get_crm_store
from keprix.discovery import bootstrap_discovery
from keprix.discovery.runner import DiscoveryJobRunner

MAX_REPLENISH_COUNT = 500


def trigger_replenish(
    workspace_id: str,
    batch_id: str,
    sent_count: int,
    *,
    store: CrmStore | None = None,
    runner: DiscoveryJobRunner | None = None,
    actor_type: str = "system",
    actor_id: str | None = None,
) -> dict[str, Any]:
    """Create one bounded discovery job for a successfully sent batch.

    The unique workspace/batch key is claimed before the discovery job is created,
    so retries cannot fan out duplicate discovery work.
    """
    store = store or get_crm_store()
    if int(sent_count) < 0:
        raise ValueError("sent_count must be >= 0")
    settings = store.get_replenish_settings(workspace_id)
    ratio = float(settings.get("ratio", 1.0))
    if ratio < 0:
        raise ValueError("replenish_ratio must be >= 0")
    target = min(MAX_REPLENISH_COUNT, max(0, math.ceil(int(sent_count) * ratio)))
    existing = store.create_replenish_event(
        workspace_id, batch_id=batch_id, sent_count=int(sent_count), ratio=ratio,
        enqueued_count=target, status="claimed",
    )
    if existing and existing.get("status") != "claimed":
        return {"event": existing, "idempotent": True, "enqueued_count": int(existing.get("enqueued_count") or 0)}
    if existing and existing.get("status") == "claimed" and existing.get("discovery_job_id"):
        return {"event": existing, "idempotent": True, "enqueued_count": int(existing.get("enqueued_count") or 0)}
    if target == 0:
        event = store.update_replenish_event(workspace_id, str(existing["id"]), status="done")
        return {"event": event, "idempotent": False, "enqueued_count": 0}
    try:
        bootstrap_discovery()
        runner = runner or DiscoveryJobRunner(store=store)
        job = runner.create_job(
            workspace_id,
            str(settings.get("adapter") or "web_directory"),
            query={"text": "replenish", "limit": target},
            params={"replenish_batch_id": batch_id, "replenish": True, "source": "replenish"},
            domain_pack=str(settings.get("domain_pack") or "generic"),
            limits={"max_results": target, "max_pages": 1},
            list_name=f"Replenished {batch_id}",
            auto_materialize=True,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        event = store.update_replenish_event(workspace_id, str(existing["id"]), status="enqueued", discovery_job_id=job["id"])
        return {"event": event, "job": job, "idempotent": False, "enqueued_count": target}
    except Exception as exc:
        event = store.update_replenish_event(workspace_id, str(existing["id"]), status="failed", error=str(exc))
        raise RuntimeError("replenish_discovery_enqueue_failed") from exc
