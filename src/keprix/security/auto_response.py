"""Automatic incident response based on Scout signal volume."""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict, deque
from typing import Any

from keprix.incident.severity import IncidentLevel
from keprix.incident.response import declare_incident
from keprix.security.scout_control import block_session
from keprix.security.sentinel_client import (
    ensure_sentinel_health,
    sentinel_available,
    sentinel_block_egress,
    sentinel_kill_agent,
    sentinel_protect_files,
)

logger = logging.getLogger(__name__)

_WINDOW_SECONDS = 600
_L3_THRESHOLD = 3
_L4_THRESHOLD = 5

_session_events: dict[str, deque[float]] = defaultdict(deque)
_product_events: dict[str, deque[float]] = defaultdict(deque)
_triggered: set[str] = set()


def _prune(bucket: deque[float], now: float) -> None:
    while bucket and now - bucket[0] > _WINDOW_SECONDS:
        bucket.popleft()


def _allow_kill() -> bool:
    return os.environ.get("SENTINEL_ALLOW_KILL", "0").strip() == "1"


def _escalate_l4_to_sentinel() -> None:
    """Best-effort kernel egress block + file protect when Sentinel socket exists."""
    if not sentinel_available():
        return
    try:
        if not sentinel_block_egress():
            logger.warning("sentinel_block_egress returned not-ok")
        if not sentinel_protect_files():
            logger.warning("sentinel_protect_files returned not-ok")
    except Exception as exc:
        logger.warning("sentinel L4 escalation failed: %s", exc)


def _escalate_l3_to_sentinel() -> None:
    """Session block is Python-side; kill only if SENTINEL_ALLOW_KILL=1."""
    if not sentinel_available():
        return
    if not _allow_kill():
        logger.info("sentinel kill skipped (SENTINEL_ALLOW_KILL!=1)")
        return
    try:
        if not sentinel_kill_agent(os.getpid()):
            logger.warning("sentinel_kill_agent returned not-ok")
    except Exception as exc:
        logger.warning("sentinel L3 escalation failed: %s", exc)


def check_sentinel_or_fallback() -> dict[str, Any]:
    """Probe Sentinel health; force egress block when SENTINEL_REQUIRED=1."""
    return ensure_sentinel_health()


def evaluate_signal(
    *,
    session_id: str | None,
    product_id: str | None,
    severity: str,
    action: str,
) -> dict[str, Any] | None:
    sev = str(severity or "").lower()
    if sev not in {"critical", "emergency"}:
        return None
    now = time.time()
    key = session_id or f"product:{product_id or 'keprix'}"
    bucket = _session_events[key]
    bucket.append(now)
    _prune(bucket, now)

    product_key = product_id or "keprix"
    product_bucket = _product_events[product_key]
    product_bucket.append(now)
    _prune(product_bucket, now)

    if len(product_bucket) >= _L4_THRESHOLD and f"l4:{product_key}" not in _triggered:
        _triggered.add(f"l4:{product_key}")
        _escalate_l4_to_sentinel()
        return declare_incident(
            level=IncidentLevel.L4_EMERGENCY,
            reason=f"auto_response:{action}",
            product_id=product_key,
            session_id=session_id,
        )

    if len(bucket) >= _L3_THRESHOLD and f"l3:{key}" not in _triggered:
        _triggered.add(f"l3:{key}")
        if session_id:
            block_session(session_id)
        _escalate_l3_to_sentinel()
        return declare_incident(
            level=IncidentLevel.L3_CRITICAL,
            reason=f"auto_response:{action}",
            product_id=product_key,
            session_id=session_id,
        )
    return None


def reset_auto_response_state() -> None:
    _session_events.clear()
    _product_events.clear()
    _triggered.clear()
