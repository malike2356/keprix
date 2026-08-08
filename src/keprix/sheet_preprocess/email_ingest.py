"""Optional IMAP email ingest for spreadsheet attachments (disabled by default).

Set ``KEPRIX_SHEET_EMAIL_INGEST=1`` to enable polling. Soft Wall still gates any
CRM write; this module only downloads attachments into the sheet upload dir and
creates enrichment jobs of type ``sheet_preprocess`` (visible on ``/crm/jobs``).

Default: disabled (``KEPRIX_SHEET_EMAIL_INGEST=0``).
"""

from __future__ import annotations

import os
from typing import Any


def email_ingest_enabled() -> bool:
    raw = os.environ.get("KEPRIX_SHEET_EMAIL_INGEST", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def status() -> dict[str, Any]:
    return {
        "enabled": email_ingest_enabled(),
        "env": "KEPRIX_SHEET_EMAIL_INGEST",
        "default": "0",
        "note": (
            "IMAP poller stub. When enabled, attachment downloads land as "
            "sheet_preprocess uploads; propose/apply still require Soft Wall "
            "before CRM upsert."
        ),
    }


def poll_once(*, workspace_id: str = "default") -> dict[str, Any]:
    """
    Stub poll. Returns a structured skip when disabled.

    A future implementation may connect via IMAP using workspace vault
    credentials, save CSV/XLSX attachments via ``service.save_upload``, and
    create propose jobs. CRM writes must still go through Soft Wall apply.
    """
    if not email_ingest_enabled():
        return {
            "ok": True,
            "skipped": True,
            "reason": "email_ingest_disabled",
            "status": status(),
            "workspace_id": workspace_id,
            "ingested": [],
        }
    # Enabled but not fully implemented: honest no-op with clear status.
    return {
        "ok": True,
        "skipped": True,
        "reason": "email_ingest_not_configured",
        "status": status(),
        "workspace_id": workspace_id,
        "ingested": [],
        "hint": (
            "Configure IMAP credentials and implement poller body; "
            "attachments must call save_upload then propose_sheet."
        ),
    }
