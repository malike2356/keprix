"""Email approval gate (prompt 11): route outbound email through Soft Wall.

First-contact (no prior sent to a recipient) and bulk (>= 5 recipients) sends
require an approved CRM Soft Wall approval whose payload hash matches this exact
recipient set + subject + body. Reply-thread sends to an existing recipient are
not gated. Loopback/local operator stays trusted.

This gate lives in the send layer; the scheduler and agent tools also route
through send_email / send_draft, so wiring it here covers every path.

The prior-sent ledger is durable (crm_email_sent_log) and keyed by
(workspace, address). It is only written AFTER a send actually succeeds, so a
failed send never marks the address "contacted" and never consumes the approval.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from keprix.crm.store import get_crm_store

BULK_THRESHOLD = 5

_APPROVAL_KIND = "email_first_contact"
_BULK_KIND = "email_bulk_send"

_SENT_LOG_DDL = """
CREATE TABLE IF NOT EXISTS crm_email_sent_log (
    workspace_id TEXT NOT NULL,
    address TEXT NOT NULL,
    first_sent_at TEXT NOT NULL,
    UNIQUE(workspace_id, address)
);
"""


def _utcnow() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _ensure_sent_log(store: Any) -> None:
    try:
        store._conn.executescript(_SENT_LOG_DDL)
        store._conn.commit()
    except Exception:  # noqa: BLE001 - pg_compat may not have executescript; best-effort
        pass


def _has_prior_sent(store: Any, workspace_id: str, address: str) -> bool:
    _ensure_sent_log(store)
    try:
        row = store._conn.execute(
            "SELECT 1 FROM crm_email_sent_log WHERE workspace_id = ? AND address = ?",
            (workspace_id, str(address).strip().lower()),
        ).fetchone()
        return row is not None
    except Exception:  # noqa: BLE001
        return False


def record_sent(store: Any, workspace_id: str, address: str) -> None:
    """Mark an address as contacted. Call ONLY after a successful send."""
    _ensure_sent_log(store)
    try:
        store._conn.execute(
            "INSERT OR IGNORE INTO crm_email_sent_log (workspace_id, address, first_sent_at) VALUES (?, ?, ?)",
            (workspace_id, str(address).strip().lower(), _utcnow()),
        )
        store._conn.commit()
    except Exception:  # noqa: BLE001
        pass


def _payload_hash(to_list: list[str], subject: str, body: str) -> str:
    normalized = json.dumps(
        {"to": sorted(str(a).strip().lower() for a in to_list), "subject": subject, "body": body},
        sort_keys=True,
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def require_approval(workspace_id: str, to_list: list[str]) -> tuple[bool, str]:
    """Return (requires_approval, reason)."""
    recipients = [str(a).strip().lower() for a in (to_list or []) if str(a).strip()]
    if not recipients:
        return False, "no_recipients"
    if len(recipients) >= BULK_THRESHOLD:
        return True, "bulk"
    store = get_crm_store()
    for address in recipients:
        if not _has_prior_sent(store, workspace_id, address):
            return True, "first_contact"
    return False, "existing_recipients"


def is_loopback_trusted(user: dict[str, Any]) -> bool:
    """Loopback / local operator stays trusted (matches the aiva2 rule)."""
    role = str((user or {}).get("role") or "")
    username = str((user or {}).get("username") or "")
    return role in {"admin", "owner"} and username in {"local", "admin", "default"}


def request_approval(
    workspace_id: str,
    *,
    to_list: list[str],
    subject: str,
    body: str,
    reason: str,
    actor_id: str | None = None,
) -> dict[str, Any]:
    from keprix.crm.soft_wall import create_crm_approval

    kind = _BULK_KIND if reason == "bulk" else _APPROVAL_KIND
    approval = create_crm_approval(
        workspace_id,
        kind=kind,
        subject=f"Email send to {len(to_list)} recipient(s): {subject[:120]}",
        payload={
            "to": [str(a).strip().lower() for a in to_list],
            "subject": subject,
            "body_hash": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "payload_hash": _payload_hash(to_list, subject, body),
            "reason": reason,
        },
        object_type="email_send",
        recipient=", ".join(str(a).strip() for a in to_list),
        actor_id=actor_id,
    )
    return {"requires_approval": True, "reason": reason, "approval": approval}


def find_approved_approval(
    workspace_id: str,
    *,
    to_list: list[str],
    subject: str,
    body: str,
) -> dict[str, Any] | None:
    """Return the approved approval matching this exact payload, or None."""
    from keprix.crm.soft_wall import pending_crm_approvals  # noqa: F401 (reuse ops store)
    from keprix.outreach.ops import get_outreach_ops_store

    ops = get_outreach_ops_store()
    target_hash = _payload_hash(to_list, subject, body)
    rows = ops.list_approvals(workspace_id, status="approved")
    for row in rows:
        payload = {}
        raw = row.get("payload_json") or row.get("draft_body") or ""
        if isinstance(raw, str):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
        if isinstance(payload, dict) and payload.get("payload_hash") == target_hash:
            return row
    return None
