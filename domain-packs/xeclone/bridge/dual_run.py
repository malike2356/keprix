"""Carina dual-run bridge: shadow compare without publish; no OAuth tokens."""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from typing import Any

_LOCK = threading.RLock()
_COMPARISONS: list[dict[str, Any]] = []
_CIRCUIT_OPEN = False


def reset_bridge() -> None:
    global _CIRCUIT_OPEN
    with _LOCK:
        _COMPARISONS.clear()
        _CIRCUIT_OPEN = False


def set_circuit(*, open_breaker: bool) -> None:
    global _CIRCUIT_OPEN
    _CIRCUIT_OPEN = bool(open_breaker)


def circuit_open() -> bool:
    return bool(_CIRCUIT_OPEN)


def _redact(payload: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in payload.items():
        lk = k.lower()
        if any(s in lk for s in ("token", "oauth", "secret", "password", "api_key")):
            continue
        out[k] = v
    return out


def shadow_compare(
    *,
    redacted_input: dict[str, Any],
    worker_id: str,
    persona_version: str,
    tenant: str,
    correlation_id: str,
    keprix_draft: dict[str, Any],
    carina_draft: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Same redacted input to Carina and Keprix; never publish shadow output."""
    safe_in = _redact(redacted_input)
    carina = carina_draft or {
        "source": "carina",
        "text": f"[carina-shadow] {safe_in.get('prompt') or safe_in.get('text') or ''}",
        "persona_version": persona_version,
    }
    keprix = dict(keprix_draft)
    keprix.setdefault("source", "keprix")
    keprix.setdefault("persona_version", persona_version)
    row = {
        "comparison_id": f"cmp_{uuid.uuid4().hex[:12]}",
        "worker_id": worker_id,
        "persona_version": persona_version,
        "tenant": tenant,
        "correlation_id": correlation_id,
        "input_hash": hashlib.sha256(json.dumps(safe_in, sort_keys=True).encode()).hexdigest(),
        "carina": carina,
        "keprix": keprix,
        "publish_allowed": False,
        "shadow": True,
        "dual_write_memory": False,
        "wave": 1,
        "memory_authority": "keprix_draft_only",
        "at": time.time(),
    }
    with _LOCK:
        _COMPARISONS.append(row)
    return {
        "ok": True,
        "comparison": row,
        "publish_blocked": True,
        "note": "shadow_output_never_publishes",
    }


def bridge_envelope(
    *,
    worker_id: str,
    persona_version: str,
    approval_id: str | None,
    keprix_run_id: str,
    tenant: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Bridge metadata only; never includes OAuth tokens."""
    return {
        "worker_id": worker_id,
        "persona_version": persona_version,
        "approval_id": approval_id,
        "keprix_run_id": keprix_run_id,
        "tenant": tenant,
        "correlation_id": correlation_id,
        "oauth_tokens_included": False,
        "bulk_private_archive": False,
    }


def fallback_to_carina(*, action: str, already_emitted: bool) -> dict[str, Any]:
    """Circuit breaker: fall back without duplicate draft/approval/notification/publish."""
    if already_emitted:
        return {
            "ok": True,
            "fallback": "carina",
            "action": action,
            "duplicate_suppressed": True,
            "created_draft": False,
            "created_approval": False,
            "created_notification": False,
            "created_publish": False,
        }
    return {
        "ok": True,
        "fallback": "carina",
        "action": action,
        "duplicate_suppressed": False,
        "note": "carina_owns_side_effect",
    }


def list_comparisons() -> list[dict[str, Any]]:
    with _LOCK:
        return [dict(c) for c in _COMPARISONS]
