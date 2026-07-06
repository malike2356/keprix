"""Monthly LLM budget alert notifications (Prompt 148)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.auth.config import data_dir
from keprix.backend.notifications.inbox import get_inbox_service
from keprix.usage.budget import get_llm_usage_budget_store
from keprix.usage.config import get_llm_usage_config

logger = logging.getLogger(__name__)

_STATE_FILE = "llm_budget_alert_state.json"


def _state_path() -> Path:
    return Path(data_dir()) / _STATE_FILE


def _load_state() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _debounce_key(workspace_id: str, month_start: str, threshold_percent: int) -> str:
    month = month_start[:7]
    return f"{workspace_id}:{month}:{threshold_percent}"


def _already_alerted(key: str) -> bool:
    return bool(_load_state().get(key))


def _mark_alerted(key: str) -> None:
    state = _load_state()
    state[key] = datetime.now(timezone.utc).isoformat()
    _save_state(state)


async def _maybe_emit_governance_event(workspace_id: str, status: dict[str, Any]) -> None:
    try:
        from keprix.governance.event_reporter import queue_audit_event

        await queue_audit_event(
            "usage_limit_warning",
            {
                "workspace_id": workspace_id,
                "spent_usd": status.get("spent_usd"),
                "monthly_budget_usd": status.get("monthly_budget_usd"),
                "percent_used": status.get("percent_used"),
                "source": "llm_budget_alert",
            },
        )
    except Exception:
        logger.debug("Governance event skipped for LLM budget alert", exc_info=True)


async def check_workspace_budget_alert(workspace_id: str = "default") -> bool:
    """Send at most one in-app alert per workspace/month/threshold crossing."""
    if not get_llm_usage_config().enabled:
        return False

    status = await get_llm_usage_budget_store().budget_status(workspace_id)
    budget = status.get("monthly_budget_usd")
    if budget is None or float(budget) <= 0:
        return False
    if not status.get("alert"):
        return False

    month_start = str(status.get("month_start_utc") or "")
    threshold = int(status.get("alert_threshold_percent") or 80)
    key = _debounce_key(workspace_id, month_start, threshold)
    if _already_alerted(key):
        return False

    spent = float(status.get("spent_usd") or 0)
    percent = float(status.get("percent_used") or 0)
    message = (
        f"Month-to-date LLM spend is ${spent:.2f} "
        f"({percent:.1f}% of ${float(budget):.2f} monthly budget)."
    )
    await get_inbox_service().send_notification(
        workspace_id,
        "llm_budget_alert",
        severity="warning",
        title="LLM spend approaching monthly budget",
        message=message,
        href="/dashboard/usage",
        metadata={
            "spent_usd": spent,
            "monthly_budget_usd": float(budget),
            "percent_used": percent,
            "alert_threshold_percent": threshold,
        },
        source="llm_usage",
    )
    _mark_alerted(key)
    await _maybe_emit_governance_event(workspace_id, status)
    return True


async def check_all_workspace_budget_alerts() -> int:
    sent = 0
    if await check_workspace_budget_alert("default"):
        sent += 1
    return sent
