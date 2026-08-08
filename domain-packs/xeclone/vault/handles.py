"""Vault handles only; never export raw secrets."""

from __future__ import annotations

import hashlib
import threading
from typing import Any

_LOCK = threading.RLock()
_HANDLES: dict[str, dict[str, Any]] = {}


def reset_vault() -> None:
    with _LOCK:
        _HANDLES.clear()


def put_secret_handle(*, name: str, purpose: str, scope: str) -> dict[str, Any]:
    handle_id = f"vh_{hashlib.sha256(f'{name}:{purpose}:{scope}'.encode()).hexdigest()[:16]}"
    row = {
        "handle_id": handle_id,
        "name": name,
        "purpose": purpose,
        "scope": scope,
        "raw_secret_exported": False,
    }
    with _LOCK:
        _HANDLES[handle_id] = row
    return dict(row)


def resolve_handle(handle_id: str) -> dict[str, Any] | None:
    with _LOCK:
        row = _HANDLES.get(handle_id)
        if not row:
            return None
        # Intentionally return metadata only
        return {"handle_id": handle_id, "name": row["name"], "purpose": row["purpose"], "scope": row["scope"]}


def revoke_all() -> dict[str, Any]:
    with _LOCK:
        count = len(_HANDLES)
        _HANDLES.clear()
    return {"revoked_handles": count, "secrets_included": False}
