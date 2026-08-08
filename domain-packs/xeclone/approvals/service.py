"""Approval preview with content hashes; material edits invalidate."""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from typing import Any

_LOCK = threading.RLock()
_APPROVALS: dict[str, dict[str, Any]] = {}


def reset_approvals() -> None:
    with _LOCK:
        _APPROVALS.clear()


def _hash_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def submit_preview(
    *,
    content: str,
    channel: str,
    audience: str,
    persona_version: str,
    disclosure: bool = True,
    links: list[str] | None = None,
    media_hash: str | None = None,
    schedule_at: str | None = None,
    cost: str = "fixture",
    factual_sources: list[str] | None = None,
    ttl_seconds: int = 3600,
    private_reply: bool = False,
) -> dict[str, Any]:
    preview = {
        "content": content,
        "channel": channel,
        "audience": audience,
        "persona_version": persona_version,
        "disclosure": disclosure,
        "links": list(links or []),
        "media_hash": media_hash,
        "schedule_at": schedule_at,
        "cost": cost,
        "factual_sources": list(factual_sources or []),
        "private_reply": private_reply,
    }
    approval_id = f"appr_{uuid.uuid4().hex[:12]}"
    row = {
        "approval_id": approval_id,
        "status": "pending",
        "preview": preview,
        "content_hash": _hash_payload(preview),
        "created_at": time.time(),
        "expires_at": time.time() + ttl_seconds,
        "decided_at": None,
        "actor_id": None,
        "owner_reviewed": bool(private_reply),
        "material_edit_invalidated": False,
    }
    with _LOCK:
        _APPROVALS[approval_id] = row
    return dict(row)


def decide(approval_id: str, *, approved: bool, actor_id: str, content_hash: str | None = None) -> dict[str, Any]:
    with _LOCK:
        row = _APPROVALS.get(approval_id)
        if not row:
            return {"ok": False, "error": "approval_not_found"}
        if row["status"] != "pending":
            return {"ok": False, "error": "already_decided", "approval": dict(row)}
        if time.time() > float(row["expires_at"]):
            row["status"] = "expired"
            return {"ok": False, "error": "expired", "approval": dict(row)}
        if content_hash and content_hash != row["content_hash"]:
            row["material_edit_invalidated"] = True
            row["status"] = "invalidated"
            return {"ok": False, "error": "material_edit_invalidates", "approval": dict(row)}
        row["status"] = "approved" if approved else "rejected"
        row["actor_id"] = actor_id
        row["decided_at"] = time.time()
        return {"ok": True, "approval": dict(row)}


def apply_material_edit(approval_id: str, new_content: str) -> dict[str, Any]:
    with _LOCK:
        row = _APPROVALS.get(approval_id)
        if not row:
            return {"ok": False, "error": "approval_not_found"}
        preview = dict(row["preview"])
        preview["content"] = new_content
        row["preview"] = preview
        row["content_hash"] = _hash_payload(preview)
        row["material_edit_invalidated"] = True
        row["status"] = "invalidated"
        return {"ok": True, "approval": dict(row)}


def get_approval(approval_id: str) -> dict[str, Any] | None:
    with _LOCK:
        row = _APPROVALS.get(approval_id)
        return dict(row) if row else None


def can_publish(approval_id: str) -> dict[str, Any]:
    with _LOCK:
        row = _APPROVALS.get(approval_id)
        if not row:
            return {"ok": False, "error": "approval_not_found"}
        if row["status"] != "approved":
            return {"ok": False, "error": f"status_{row['status']}"}
        if time.time() > float(row["expires_at"]):
            row["status"] = "expired"
            return {"ok": False, "error": "expired"}
        if row.get("material_edit_invalidated"):
            return {"ok": False, "error": "material_edit_invalidates"}
        return {"ok": True, "approval": dict(row)}
