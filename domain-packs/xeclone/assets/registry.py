"""Asset registry for identity media references (no raw biometrics)."""

from __future__ import annotations

import hashlib
import threading
import time
from typing import Any

_LOCK = threading.RLock()
_ASSETS: dict[str, dict[str, Any]] = {}


def reset_assets() -> None:
    with _LOCK:
        _ASSETS.clear()


def register_asset(
    *,
    asset_id: str,
    owner_subject_id: str,
    subject_id: str,
    media_type: str,
    content: str = "",
    capture_source: str = "owner_upload",
    allowed_uses: list[str] | None = None,
    allowed_providers: list[str] | None = None,
    retention_days: int = 90,
) -> dict[str, Any]:
    digest = hashlib.sha256((content or asset_id).encode("utf-8")).hexdigest()
    row = {
        "asset_id": asset_id,
        "owner_subject_id": owner_subject_id,
        "subject_id": subject_id,
        "media_type": media_type,
        "hash": digest,
        "capture_source": capture_source,
        "allowed_uses": list(allowed_uses or ["generate", "transform"]),
        "allowed_providers": list(allowed_providers or ["stub-tts", "stub-image", "stub-video"]),
        "quality": "fixture",
        "retention_days": retention_days,
        "deletion_state": "active",
        "registered_at": time.time(),
    }
    with _LOCK:
        _ASSETS[asset_id] = row
    return dict(row)


def get_asset(asset_id: str) -> dict[str, Any] | None:
    with _LOCK:
        row = _ASSETS.get(asset_id)
        return dict(row) if row else None


def mark_deleted(asset_id: str) -> dict[str, Any]:
    with _LOCK:
        row = _ASSETS.get(asset_id)
        if not row:
            return {"asset_id": asset_id, "status": "missing"}
        row["deletion_state"] = "deleted"
        return dict(row)
