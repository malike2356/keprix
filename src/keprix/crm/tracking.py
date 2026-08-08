"""Optional open/click tracking with privacy defaults (prompt 460)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from keprix.crm.data_quality import get_nice_settings, upsert_nice_settings
from keprix.crm.nice_schema import ensure_nice_schema

DISCLOSURE = (
    "This message may include optional open/click measurement when enabled. "
    "You can opt out of tracking; opens are never treated as a buying signal."
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def tracking_enabled_for_campaign(store: Any, workspace_id: str, *, campaign_override: bool | None = None) -> bool:
    settings = get_nice_settings(store, workspace_id)
    workspace_on = bool(settings.get("tracking_enabled"))
    if campaign_override is None:
        return workspace_on
    return bool(campaign_override)


def set_workspace_tracking(store: Any, workspace_id: str, enabled: bool) -> dict[str, Any]:
    return upsert_nice_settings(store, workspace_id, tracking_enabled=enabled)


def wrap_links(
    store: Any,
    workspace_id: str,
    *,
    html_or_text: str,
    campaign_id: str | None = None,
    contact_key: str | None = None,
    campaign_override: bool | None = None,
) -> dict[str, Any]:
    """When tracking off, return raw links unchanged. When on, wrap once with honest token."""
    enabled = tracking_enabled_for_campaign(store, workspace_id, campaign_override=campaign_override)
    if not enabled:
        return {
            "enabled": False,
            "body": html_or_text,
            "pixel": None,
            "disclosure": None,
            "wrapped_count": 0,
        }
    # Contact-level opt-out via suppression channel=tracking
    if contact_key and store.is_suppressed(workspace_id, channel="tracking", address=contact_key):
        return {
            "enabled": False,
            "body": html_or_text,
            "pixel": None,
            "disclosure": None,
            "wrapped_count": 0,
            "opted_out": True,
        }

    wrapped_count = 0
    body = html_or_text
    # Simple URL wrap for http(s) tokens (once).
    tokens = []
    for part in body.split():
        if part.startswith("http://") or part.startswith("https://"):
            if "kpx_t=" in part:
                tokens.append(part)
                continue
            token = _click_token(workspace_id, campaign_id, contact_key, part)
            wrapped = f"/api/crm/tracking/click?t={token}"
            tokens.append(wrapped)
            wrapped_count += 1
            _remember_raw(store, workspace_id, token, part, campaign_id, contact_key)
        else:
            tokens.append(part)
    body_out = " ".join(tokens)
    pixel_token = _click_token(workspace_id, campaign_id, contact_key, "pixel")
    pixel = f"/api/crm/tracking/open.gif?t={pixel_token}"
    if DISCLOSURE not in body_out:
        body_out = f"{body_out}\n\n{DISCLOSURE}"
    return {
        "enabled": True,
        "body": body_out,
        "pixel": pixel,
        "disclosure": DISCLOSURE,
        "wrapped_count": wrapped_count,
    }


_RAW_CACHE: dict[str, dict[str, Any]] = {}


def _click_token(workspace_id: str, campaign_id: str | None, contact_key: str | None, raw: str) -> str:
    return hashlib.sha256(f"{workspace_id}|{campaign_id}|{contact_key}|{raw}".encode()).hexdigest()[:24]


def _remember_raw(
    store: Any,
    workspace_id: str,
    token: str,
    raw_url: str,
    campaign_id: str | None,
    contact_key: str | None,
) -> None:
    _RAW_CACHE[token] = {
        "workspace_id": workspace_id,
        "raw_url": raw_url,
        "campaign_id": campaign_id,
        "contact_key": contact_key,
    }


def record_event(
    store: Any,
    workspace_id: str,
    *,
    event_type: str,
    token: str | None = None,
    url: str | None = None,
    campaign_id: str | None = None,
    contact_key: str | None = None,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    meta = _RAW_CACHE.get(token or "", {})
    raw_url = meta.get("raw_url") or url
    campaign_id = campaign_id or meta.get("campaign_id")
    contact_key = contact_key or meta.get("contact_key")

    # Dedupe opens: one open per contact/campaign/day.
    if event_type == "open" and contact_key:
        day = _utcnow()[:10]
        existing = store._fetchall(
            """
            SELECT id FROM crm_tracking_events
            WHERE workspace_id = ? AND event_type = 'open' AND contact_key = ?
              AND substr(created_at, 1, 10) = ?
              AND IFNULL(campaign_id, '') = IFNULL(?, '')
            """,
            (ws, contact_key, day, campaign_id),
        )
        if existing:
            return {"ok": True, "deduped": True, "signal_strength": "weak_noise"}

    rid = str(uuid.uuid4())
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO crm_tracking_events (
                id, workspace_id, campaign_id, contact_key, event_type, url, raw_url, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, '{}', ?)
            """,
            (rid, ws, campaign_id, contact_key, event_type, url, raw_url, _utcnow()),
        )
        store._conn.commit()
    return {
        "ok": True,
        "event_id": rid,
        "event_type": event_type,
        "raw_url": raw_url,
        # Stage machine must not treat open as buying signal.
        "stage_signal": None if event_type == "open" else ("weak" if event_type == "click" else None),
        "buying_signal": False,
    }


def resolve_click(token: str) -> dict[str, Any] | None:
    return _RAW_CACHE.get(token)


def list_events(store: Any, workspace_id: str, *, event_type: str | None = None) -> list[dict[str, Any]]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    if event_type:
        return store._fetchall(
            "SELECT * FROM crm_tracking_events WHERE workspace_id = ? AND event_type = ? ORDER BY created_at DESC",
            (ws, event_type),
        )
    return store._fetchall(
        "SELECT * FROM crm_tracking_events WHERE workspace_id = ? ORDER BY created_at DESC",
        (ws,),
    )
