"""Shared UI status vocabulary."""

from __future__ import annotations

STATUS_VOCABULARY: dict[str, dict[str, str]] = {
    "draft": {"label": "Draft", "role": "muted"},
    "ready": {"label": "Ready", "role": "info"},
    "running": {"label": "Running", "role": "primary"},
    "waiting": {"label": "Waiting", "role": "warning"},
    "needs_approval": {"label": "Needs approval", "role": "warning"},
    "blocked": {"label": "Blocked", "role": "danger"},
    "failed": {"label": "Failed", "role": "danger"},
    "complete": {"label": "Complete", "role": "success"},
    "archived": {"label": "Archived", "role": "muted"},
    "suspended": {"label": "Suspended", "role": "muted"},
    "at_risk": {"label": "At risk", "role": "danger"},
    "over_limit": {"label": "Over limit", "role": "warning"},
    "synced": {"label": "Synced", "role": "success"},
    "out_of_sync": {"label": "Out of sync", "role": "warning"},
}


def status_label(key: str) -> str:
    entry = STATUS_VOCABULARY.get(key)
    return entry["label"] if entry else key.replace("_", " ").title()
