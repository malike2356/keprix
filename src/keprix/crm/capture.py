"""Consent-first public lead capture backed by the canonical CRM store."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.crm.store import CrmStore, _normalise_email, _utcnow


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def ip_hash(ip: str) -> str:
    return hashlib.sha256((ip or "").encode("utf-8")).hexdigest()


def create_capture_link(
    store: CrmStore,
    workspace_id: str,
    *,
    label: str = "",
    default_source: str = "capture",
    redirect_url: str = "",
) -> dict[str, Any]:
    raw = secrets.token_urlsafe(32)
    link_id = f"cap_{uuid.uuid4().hex[:16]}"
    store._conn.execute(
        "INSERT INTO crm_capture_links "
        "(id, workspace_id, token_hash, label, default_source, redirect_url, active, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
        (link_id, workspace_id, token_hash(raw), label.strip(), default_source.strip() or "capture", redirect_url.strip(), _utcnow()),
    )
    store._conn.commit()
    return {"id": link_id, "token": raw, "workspace_id": workspace_id, "label": label, "default_source": default_source, "redirect_url": redirect_url, "active": True}


def list_capture_links(store: CrmStore, workspace_id: str) -> list[dict[str, Any]]:
    rows = store._conn.execute(
        "SELECT id, workspace_id, label, default_source, redirect_url, active, created_at, rotated_at "
        "FROM crm_capture_links WHERE workspace_id = ? ORDER BY created_at DESC",
        (workspace_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def set_capture_link_active(store: CrmStore, workspace_id: str, link_id: str, active: bool) -> bool:
    cur = store._conn.execute(
        "UPDATE crm_capture_links SET active = ?, rotated_at = ? WHERE workspace_id = ? AND id = ?",
        (1 if active else 0, _utcnow() if not active else "", workspace_id, link_id),
    )
    store._conn.commit()
    return cur.rowcount == 1


def rotate_capture_link(store: CrmStore, workspace_id: str, link_id: str) -> dict[str, Any] | None:
    row = store._conn.execute(
        "SELECT label, default_source, redirect_url FROM crm_capture_links WHERE workspace_id = ? AND id = ?",
        (workspace_id, link_id),
    ).fetchone()
    if row is None:
        return None
    store._conn.execute("UPDATE crm_capture_links SET active = 0, rotated_at = ? WHERE workspace_id = ? AND id = ?", (_utcnow(), workspace_id, link_id))
    store._conn.commit()
    return create_capture_link(store, workspace_id, label=row[0], default_source=row[1], redirect_url=row[2])


def _active_link(store: CrmStore, raw_token: str) -> dict[str, Any] | None:
    row = store._conn.execute(
        "SELECT * FROM crm_capture_links WHERE token_hash = ? AND active = 1",
        (token_hash(raw_token),),
    ).fetchone()
    return dict(row) if row is not None else None


def submit_capture(
    store: CrmStore,
    raw_token: str,
    *,
    email: str,
    fullname: str,
    consent: bool,
    ip: str = "",
    company: str = "",
    phone: str = "",
    source: str = "",
    campaign: str = "",
    utm: str = "",
    referrer: str = "",
    max_per_hour: int = 20,
) -> dict[str, Any]:
    address = _normalise_email(email)
    if not address or "@" not in address or not consent:
        raise ValueError("a valid email address and explicit consent are required")
    link = _active_link(store, raw_token)
    if link is None:
        raise LookupError("capture link not found")
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=1)).replace(microsecond=0).isoformat()
    token_digest = token_hash(raw_token)
    visitor_digest = ip_hash(ip)
    recent = store._conn.execute(
        "SELECT COUNT(*) FROM crm_capture_events WHERE token_hash = ? AND ip_hash = ? AND created_at >= ?",
        (token_digest, visitor_digest, since),
    ).fetchone()[0]
    if int(recent or 0) >= max_per_hour:
        raise PermissionError("capture rate limit exceeded")
    fields = {"email": address, "name": fullname.strip(), "company_name": company.strip(), "phones": phone.strip() and [{"number": phone.strip(), "primary": True}] or [], "source": source.strip() or link["default_source"], "consent_status": "consented"}
    existing = store._find_lead_key(link["workspace_id"], fields)
    lead = existing or store.create_lead(link["workspace_id"], **fields)
    status = "duplicate" if existing else "new"
    event_id = f"cap_evt_{uuid.uuid4().hex[:16]}"
    store._conn.execute(
        "INSERT INTO crm_capture_events (id, workspace_id, token_hash, email, fullname, company, phone, source, campaign, utm, referrer, consent, ip_hash, status, lead_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)",
        (event_id, link["workspace_id"], token_digest, address, fullname.strip(), company.strip(), phone.strip(), fields["source"], campaign, utm, referrer, visitor_digest, status, lead["id"], _utcnow()),
    )
    store._conn.commit()
    return {"ok": True, "status": status, "duplicate_of": lead["id"] if existing else None, "lead_id": lead["id"], "redirect_url": link["redirect_url"]}
