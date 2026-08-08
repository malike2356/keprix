"""Sidecar-down / model-down queue (PTS-03). Product core remains usable."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

_LOCK = threading.RLock()
_QUEUE: dict[str, dict[str, Any]] = {}


class DegradedQueue:
    """Queue AI work when sidecar or model is down; replay revalidates authority."""

    def __init__(self, *, default_ttl_seconds: int = 86400, max_attempts: int = 5, max_items: int = 500) -> None:
        self.default_ttl = default_ttl_seconds
        self.max_attempts = max_attempts
        self.max_items = max_items

    def reset(self) -> None:
        with _LOCK:
            _QUEUE.clear()

    def enqueue(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        node_key: str,
        payload: dict[str, Any],
        priority: int = 50,
        dedupe_key: str = "",
        authority_version: str = "",
        grant_id: str | None = None,
        approval_id: str | None = None,
    ) -> dict[str, Any]:
        with _LOCK:
            if len(_QUEUE) >= self.max_items:
                return {"status": "rejected_queue_full", "workspace_id": workspace_id}
            if dedupe_key:
                for row in _QUEUE.values():
                    if row.get("dedupe_key") == dedupe_key and row["workspace_id"] == workspace_id:
                        return {**row, "deduped": True}
            item_id = f"aiq_{uuid.uuid4().hex[:12]}"
            row = {
                "id": item_id,
                "workspace_id": workspace_id,
                "actor_id": actor_id,
                "node_key": node_key,
                "payload": payload,
                "priority": priority,
                "dedupe_key": dedupe_key,
                "authority_version": authority_version,
                "grant_id": grant_id,
                "approval_id": approval_id,
                "status": "queued",
                "attempts": 0,
                "created_at": time.time(),
                "expires_at": time.time() + self.default_ttl,
                "deduped": False,
            }
            _QUEUE[item_id] = row
            return dict(row)

    def list_visible(self, workspace_id: str) -> list[dict[str, Any]]:
        now = time.time()
        with _LOCK:
            rows = [dict(r) for r in _QUEUE.values() if r["workspace_id"] == workspace_id]
        return sorted(
            [r for r in rows if r["expires_at"] >= now],
            key=lambda r: (-int(r["priority"]), r["created_at"]),
        )

    def replay(
        self,
        item_id: str,
        *,
        current_authority_version: str,
        grant_still_valid: bool,
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
            if row.get("authority_version") and row["authority_version"] != current_authority_version:
                row["status"] = "rejected_stale_authority"
                return dict(row)
            if row.get("grant_id") and not grant_still_valid:
                row["status"] = "rejected_stale_grant"
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
