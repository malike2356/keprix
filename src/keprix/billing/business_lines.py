"""Workspace-scoped business-line entitlement and durable registry."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from keprix.billing.config_loader import load_billing_config
from keprix.billing.store import get_billing_store

_TIERS = {"community": 0, "starter": 1, "pro": 2, "team": 3, "business": 4, "enterprise": 5}


def _path() -> Path:
    root = Path(os.environ.get("KEPRIX_HOME", Path.home() / ".keprix")) / "billing"
    root.mkdir(parents=True, exist_ok=True)
    return root / "business_lines.json"


def _read() -> dict[str, list[dict[str, Any]]]:
    path = _path()
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write(data: dict[str, list[dict[str, Any]]]) -> None:
    path = _path()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temporary.replace(path)


def business_lines_included_below_business() -> int:
    config = load_billing_config()
    return config.business_lines_included_below_business if config else 1


def business_lines_unlimited_min_tier() -> str:
    config = load_billing_config()
    return (config.business_lines_unlimited_min_tier if config else "business").strip().lower() or "business"


def list_workspace_business_lines(workspace_id: str, *, include_deleted: bool = False) -> list[dict[str, Any]]:
    rows = _read().get(str(workspace_id), [])
    return rows if include_deleted else [row for row in rows if not row.get("deleted_at")]


def count_workspace_business_lines(workspace_id: str) -> int:
    return len(list_workspace_business_lines(workspace_id))


def current_tier_for_user(user_id: str) -> str:
    explicit = (os.environ.get("KEPRIX_BUSINESS_LINE_TIER") or os.environ.get("KEPRIX_HOSTED_PLAN") or "").strip().lower()
    return explicit if explicit in _TIERS else "community"


async def resolved_current_tier(user_id: str) -> str:
    explicit = (os.environ.get("KEPRIX_BUSINESS_LINE_TIER") or os.environ.get("KEPRIX_HOSTED_PLAN") or "").strip().lower()
    if explicit in _TIERS:
        return explicit
    subscription = await get_billing_store().get_subscription(user_id)
    plan_id = str((subscription or {}).get("plan_id") or "").strip().lower()
    return plan_id if plan_id in _TIERS else "community"


def workspace_can_add_business_line(workspace_id: str, current_tier: str | None = None) -> bool:
    tier = (current_tier or current_tier_for_user("")).strip().lower()
    unlimited = _TIERS.get(tier, 0) >= _TIERS.get(business_lines_unlimited_min_tier(), 4)
    from keprix.billing.grandfathering import workspace_has_feature_grandfather
    return unlimited or count_workspace_business_lines(workspace_id) < business_lines_included_below_business() or workspace_has_feature_grandfather(workspace_id, "business_lines")


async def require_can_add_business_line(workspace_id: str, user_id: str) -> dict[str, Any]:
    tier = await resolved_current_tier(user_id)
    unlimited = _TIERS.get(tier, 0) >= _TIERS.get(business_lines_unlimited_min_tier(), 4)
    count = count_workspace_business_lines(workspace_id)
    included = business_lines_included_below_business()
    from keprix.billing.grandfathering import workspace_has_feature_grandfather
    if not unlimited and count >= included and not workspace_has_feature_grandfather(workspace_id, "business_lines"):
        raise HTTPException(
            status_code=402,
            detail={
                "message": "Business-line limit reached. Upgrade to add another business line.",
                "required_tier": business_lines_unlimited_min_tier(),
                "current_tier": tier,
            },
        )
    return {"current_tier": tier, "required_tier": business_lines_unlimited_min_tier(), "count": count, "included": included, "unlimited": unlimited}


async def business_line_status(workspace_id: str, user_id: str) -> dict[str, Any]:
    tier = await resolved_current_tier(user_id)
    count = count_workspace_business_lines(workspace_id)
    included = business_lines_included_below_business()
    unlimited = _TIERS.get(tier, 0) >= _TIERS.get(business_lines_unlimited_min_tier(), 4)
    return {
        "workspace_id": workspace_id,
        "current_count": count,
        "included": included,
        "unlimited_min_tier": business_lines_unlimited_min_tier(),
        "current_tier": tier,
        "can_add": unlimited or count < included,
        "at_limit": not unlimited and count >= included,
        "unlimited": unlimited,
    }


async def create_workspace_business_line(workspace_id: str, user_id: str, name: str) -> dict[str, Any]:
    await require_can_add_business_line(workspace_id, user_id)
    data = _read()
    row = {"id": str(uuid.uuid4()), "name": name.strip(), "workspace_id": workspace_id}
    data.setdefault(workspace_id, []).append(row)
    _write(data)
    return row


def delete_workspace_business_line(workspace_id: str, line_id: str) -> bool:
    data = _read()
    for row in data.get(workspace_id, []):
        if row.get("id") == line_id and not row.get("deleted_at"):
            row["deleted_at"] = "deleted"
            _write(data)
            return True
    return False
