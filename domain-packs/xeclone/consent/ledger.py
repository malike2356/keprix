"""Versioned, revocable consent ledger for Xeclone identity assets."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

PURPOSES = frozenset(
    {
        "ingest",
        "index",
        "train",
        "generate",
        "transform",
        "upload_to_provider",
        "publish",
        "private_message",
        "retain",
        "export",
        "delete",
    }
)

_LOCK = threading.RLock()
# asset_id -> {purpose -> {allowed, version, subject_id, revoked, revoked_at}}
_LEDGER: dict[str, dict[str, dict[str, Any]]] = {}
_OWNER_SUBJECT = "owner-laud"


def reset_ledger() -> None:
    with _LOCK:
        _LEDGER.clear()


def grant_consent(
    asset_id: str,
    purpose: str,
    *,
    subject_id: str = _OWNER_SUBJECT,
    version: str | None = None,
) -> dict[str, Any]:
    if purpose not in PURPOSES:
        raise ValueError(f"unknown_purpose:{purpose}")
    row = {
        "asset_id": asset_id,
        "purpose": purpose,
        "subject_id": subject_id,
        "allowed": True,
        "revoked": False,
        "version": version or f"c_{uuid.uuid4().hex[:10]}",
        "granted_at": time.time(),
        "revoked_at": None,
    }
    with _LOCK:
        _LEDGER.setdefault(asset_id, {})[purpose] = row
    return dict(row)


def revoke(asset_id: str, purpose: str | None = None) -> dict[str, Any]:
    with _LOCK:
        bucket = _LEDGER.get(asset_id) or {}
        if purpose:
            row = bucket.get(purpose)
            if not row:
                return {"asset_id": asset_id, "purpose": purpose, "status": "missing"}
            row["allowed"] = False
            row["revoked"] = True
            row["revoked_at"] = time.time()
            return {"asset_id": asset_id, "purpose": purpose, "status": "revoked", "version": row["version"]}
        out = []
        for p, row in bucket.items():
            row["allowed"] = False
            row["revoked"] = True
            row["revoked_at"] = time.time()
            out.append(p)
        return {"asset_id": asset_id, "status": "revoked", "purposes": out}


def check_consent(asset_id: str, purpose: str) -> dict[str, Any]:
    if purpose not in PURPOSES:
        return {"allowed": False, "denied": True, "reason": "unknown_purpose"}
    with _LOCK:
        row = (_LEDGER.get(asset_id) or {}).get(purpose)
        if not row:
            return {"allowed": False, "denied": True, "reason": "no_grant", "asset_id": asset_id, "purpose": purpose}
        if row.get("revoked") or not row.get("allowed"):
            return {
                "allowed": False,
                "denied": True,
                "reason": "revoked",
                "asset_id": asset_id,
                "purpose": purpose,
                "version": row.get("version"),
            }
        return {
            "allowed": True,
            "denied": False,
            "asset_id": asset_id,
            "purpose": purpose,
            "version": row.get("version"),
            "subject_id": row.get("subject_id"),
        }


def assert_owner_identity_input(
    *,
    asset_id: str,
    subject_id: str,
    owner_subject_id: str = _OWNER_SUBJECT,
) -> dict[str, Any]:
    if subject_id != owner_subject_id:
        return {
            "ok": False,
            "error": "other_person_media_rejected",
            "asset_id": asset_id,
            "subject_id": subject_id,
            "owner_subject_id": owner_subject_id,
        }
    return {"ok": True, "asset_id": asset_id, "subject_id": subject_id}


def snapshot() -> dict[str, Any]:
    with _LOCK:
        return {aid: {p: dict(r) for p, r in purposes.items()} for aid, purposes in _LEDGER.items()}
