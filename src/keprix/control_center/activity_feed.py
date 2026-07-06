"""Team-visible engineering activity feed."""

from __future__ import annotations

from typing import Any

from keprix.control_center.store import get_control_center_store


def recent_activity(limit: int = 50) -> list[dict[str, Any]]:
    return get_control_center_store().list_activity(limit=limit)


def list_approvals(*, status: str | None = None) -> list[dict[str, Any]]:
    approvals = get_control_center_store().list_approvals()
    if status:
        approvals = [item for item in approvals if item.get("status") == status]
    return approvals


def list_recent_artifacts(limit: int = 20) -> list[dict[str, Any]]:
    artifacts = get_control_center_store().list_artifacts()
    return list(reversed(artifacts[-limit:]))
