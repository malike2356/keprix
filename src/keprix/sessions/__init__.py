"""Session expiration, concurrent limits, and revocation (parity with shared/sessions)."""

from __future__ import annotations

import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

Tier = Literal["financial", "business", "content"]
OnLimit = Literal["kill_oldest", "block_new"]

TIER_DEFAULTS: dict[str, dict[str, Any]] = {
    "financial": {
        "idle_timeout_ms": 4 * 60 * 60 * 1000,
        "absolute_max_ms": 12 * 60 * 60 * 1000,
        "max_concurrent": 5,
        "on_limit": "kill_oldest",
    },
    "business": {
        "idle_timeout_ms": 2 * 60 * 60 * 1000,
        "absolute_max_ms": 24 * 60 * 60 * 1000,
        "max_concurrent": 5,
        "on_limit": "kill_oldest",
    },
    "content": {
        "idle_timeout_ms": 24 * 60 * 60 * 1000,
        "absolute_max_ms": 7 * 24 * 60 * 60 * 1000,
        "max_concurrent": 5,
        "on_limit": "kill_oldest",
    },
}

_PROJECT_LIMITS: dict[str, int] = {}
_REVOCATION_LOG: list[dict[str, Any]] = []
_LOG_LOCK = threading.Lock()


def resolve_session_config(
    *,
    tier: str | None = None,
    idle_timeout_ms: int | None = None,
    absolute_max_ms: int | None = None,
    max_concurrent: int | None = None,
    on_limit: str | None = None,
    project: str | None = None,
) -> dict[str, Any]:
    raw = (tier or os.environ.get("KEPRIX_SESSION_TIER") or os.environ.get("SESSION_TIER") or "business").lower()
    if raw not in TIER_DEFAULTS:
        raw = "business"
    base = TIER_DEFAULTS[raw]
    idle = int(idle_timeout_ms or os.environ.get("SESSION_IDLE_TIMEOUT_MS") or base["idle_timeout_ms"])
    absolute = int(absolute_max_ms or os.environ.get("SESSION_ABSOLUTE_MAX_MS") or base["absolute_max_ms"])
    max_c = int(max_concurrent or os.environ.get("SESSION_MAX_CONCURRENT") or base["max_concurrent"])
    policy = (on_limit or os.environ.get("SESSION_ON_LIMIT") or base["on_limit"]).lower()
    if policy not in ("kill_oldest", "block_new"):
        policy = "kill_oldest"
    return {
        "tier": raw,
        "idle_timeout_ms": idle if idle > 0 else base["idle_timeout_ms"],
        "absolute_max_ms": absolute if absolute > 0 else base["absolute_max_ms"],
        "max_concurrent": max_c if max_c > 0 else 5,
        "on_limit": policy,
        "project": project or os.environ.get("SESSION_PROJECT") or "keprix",
    }


def set_max_concurrent(project: str, limit: int) -> None:
    if project and limit > 0:
        _PROJECT_LIMITS[project] = int(limit)


def get_max_concurrent(config: dict[str, Any]) -> int:
    project = str(config.get("project") or "")
    if project and project in _PROJECT_LIMITS:
        return _PROJECT_LIMITS[project]
    return int(config.get("max_concurrent") or 5)


def parse_device_info(
    *,
    user_agent: str | None = None,
    ip: str | None = None,
    location: str | None = None,
    device_label: str | None = None,
) -> dict[str, Any]:
    ua = (user_agent or "").strip()
    browser = "Unknown browser"
    os_name = "Unknown OS"
    if re.search(r"Edg/", ua, re.I):
        browser = "Edge"
    elif re.search(r"Chrome/", ua, re.I) and not re.search(r"Chromium", ua, re.I):
        browser = "Chrome"
    elif re.search(r"Firefox/", ua, re.I):
        browser = "Firefox"
    elif re.search(r"Safari/", ua, re.I) and not re.search(r"Chrome/", ua, re.I):
        browser = "Safari"
    elif ua:
        browser = "Browser"
    if re.search(r"Windows", ua, re.I):
        os_name = "Windows"
    elif re.search(r"Android", ua, re.I):
        os_name = "Android"
    elif re.search(r"iPhone|iPad|iOS", ua, re.I):
        os_name = "iOS"
    elif re.search(r"Mac OS X|Macintosh", ua, re.I):
        os_name = "macOS"
    elif re.search(r"Linux", ua, re.I):
        os_name = "Linux"
    loc = (location or "").strip() or "Unknown location"
    label = (device_label or "").strip() or f"{browser} on {os_name}"
    return {
        "user_agent": ua or None,
        "ip": ip,
        "device_label": label,
        "location": loc,
        "browser": browser,
        "os": os_name,
    }


def format_new_login_message(*, browser: str, os_name: str, location: str) -> str:
    return f"New sign-in from {browser} on {os_name} in {location}"


def enforce_concurrent_limit(
    active_sessions: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    max_c = get_max_concurrent(config)
    on_limit = config.get("on_limit") or "kill_oldest"
    live = sorted(
        [s for s in active_sessions if not s.get("revoked_at")],
        key=lambda s: float(s.get("created_at") or 0),
    )
    if len(live) < max_c:
        return {"allowed": True, "killed_session_ids": []}
    if on_limit == "block_new":
        return {"allowed": False, "killed_session_ids": [], "reason": "blocked_at_limit"}
    overflow = len(live) - max_c + 1
    killed = [str(s.get("session_id")) for s in live[: max(overflow, 0)]]
    return {"allowed": True, "killed_session_ids": killed}


def append_revocation_log(
    *,
    user_id: str,
    session_id: str | None,
    reason: str,
    initiated_by: str = "system",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "id": str(uuid.uuid4()),
        "timestamp": time.time(),
        "user_id": user_id,
        "session_id": session_id,
        "reason": reason,
        "initiated_by": initiated_by,
        "meta": meta or {},
    }
    with _LOG_LOCK:
        _REVOCATION_LOG.append(row)
        if len(_REVOCATION_LOG) > 20_000:
            del _REVOCATION_LOG[: len(_REVOCATION_LOG) - 15_000]
    return row


def get_revocation_log(
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    limit = min(max(int(limit), 1), 500)
    out: list[dict[str, Any]] = []
    with _LOG_LOCK:
        for row in reversed(_REVOCATION_LOG):
            if len(out) >= limit:
                break
            if user_id and row.get("user_id") != user_id:
                continue
            if session_id and row.get("session_id") != session_id:
                continue
            out.append(row)
    return out


def clear_session_policy_state_for_tests() -> None:
    _PROJECT_LIMITS.clear()
    with _LOG_LOCK:
        _REVOCATION_LOG.clear()


@dataclass
class NewDeviceNotifier:
    handler: Callable[[dict[str, Any], str], None] | None = None
    banners: dict[str, str] = field(default_factory=dict)

    def notify(self, event: dict[str, Any], message: str) -> None:
        self.banners[str(event.get("user_id"))] = message
        if self.handler:
            try:
                self.handler(event, message)
            except Exception:
                pass

    def consume_banner(self, user_id: str) -> str | None:
        return self.banners.pop(user_id, None)


NEW_DEVICE_NOTIFIER = NewDeviceNotifier()
