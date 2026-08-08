"""Sidecar-down / low-bandwidth queue (spec/28, ABS-03)."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

_LOCK = threading.RLock()
_QUEUE: dict[str, dict[str, Any]] = {}


class DegradedQueue:
    """Product-owned AI work queue when Keprix is down or bandwidth is low."""

    def __init__(self, *, default_ttl_seconds: int = 86400, max_attempts: int = 5) -> None:
        self.default_ttl = default_ttl_seconds
        self.max_attempts = max_attempts

    def reset(self) -> None:
        with _LOCK:
            _QUEUE.clear()

    def enqueue(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        node_key: str,
        payload: dict[str, Any],
        priority: int = 50,
        dedupe_key: str = "",
        authority_version: str = "",
        record_version: int | None = None,
        approval_id: str | None = None,
        low_bandwidth: bool = False,
    ) -> dict[str, Any]:
        with _LOCK:
            if dedupe_key:
                for row in _QUEUE.values():
                    if row.get("dedupe_key") == dedupe_key and row["tenant_id"] == tenant_id:
                        return {**row, "deduped": True}
            item_id = f"aiq_{uuid.uuid4().hex[:12]}"
            row = {
                "id": item_id,
                "tenant_id": tenant_id,
                "actor_id": actor_id,
                "node_key": node_key,
                "payload": payload if not low_bandwidth else {"compact": True, "ref": payload.get("ref")},
                "priority": priority,
                "dedupe_key": dedupe_key,
                "authority_version": authority_version,
                "record_version": record_version,
                "approval_id": approval_id,
                "status": "queued",
                "attempts": 0,
                "created_at": time.time(),
                "expires_at": time.time() + self.default_ttl,
                "low_bandwidth": low_bandwidth,
                "deduped": False,
            }
            _QUEUE[item_id] = row
            return dict(row)

    def list_visible(self, tenant_id: str) -> list[dict[str, Any]]:
        now = time.time()
        with _LOCK:
            rows = [dict(r) for r in _QUEUE.values() if r["tenant_id"] == tenant_id]
        return sorted(
            [r for r in rows if r["expires_at"] >= now],
            key=lambda r: (-int(r["priority"]), r["created_at"]),
        )

    def replay(
        self,
        item_id: str,
        *,
        current_authority_version: str,
        current_record_version: int | None,
        approval_still_valid: bool,
        permissions_ok: bool,
    ) -> dict[str, Any]:
        with _LOCK:
            row = _QUEUE.get(item_id)
            if not row:
                raise KeyError(item_id)
            if time.time() > float(row["expires_at"]):
                row["status"] = "expired"
                return dict(row)
            # Revalidate on replay: never use stale authority
            if row.get("authority_version") and row["authority_version"] != current_authority_version:
                row["status"] = "rejected_stale_authority"
                return dict(row)
            if (
                row.get("record_version") is not None
                and current_record_version is not None
                and row["record_version"] != current_record_version
            ):
                row["status"] = "rejected_stale_record"
                return dict(row)
            if row.get("approval_id") and not approval_still_valid:
                row["status"] = "rejected_stale_approval"
                return dict(row)
            if not permissions_ok:
                row["status"] = "rejected_permissions"
                return dict(row)
            row["attempts"] += 1
            if row["attempts"] > self.max_attempts:
                row["status"] = "dead_letter"
                return dict(row)
            row["status"] = "replayed"
            return dict(row)


degraded_queue = DegradedQueue()
