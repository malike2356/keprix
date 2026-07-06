"""Data retention policy helpers."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_RETENTION_DAYS = {
    "research_jobs": 30,
    "audit_logs": 365,
    "dsar_exports": 30,
    "agent_messages": 365,
    "run_logs": 90,
    "memory_episodes": 365,
}

DEFAULT_RETENTION_ACTIONS = {
    "research_jobs": "delete",
    "audit_logs": "anonymise",
    "dsar_exports": "delete",
    "agent_messages": "anonymise",
    "run_logs": "anonymise",
    "memory_episodes": "anonymise",
}

_last_retention_run: str | None = None


def _privacy_dir() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "privacy"
    except Exception:
        root = Path.home() / ".keprix" / "privacy"
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_retention_policies() -> list[dict[str, Any]]:
    path = _privacy_dir() / "retention_policies.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return [
        {
            "data_category": category,
            "retain_days": days,
            "action": DEFAULT_RETENTION_ACTIONS.get(category, "anonymise"),
        }
        for category, days in DEFAULT_RETENTION_DAYS.items()
    ]


def set_retention_policy(data_category: str, *, retain_days: int, action: str) -> dict[str, Any]:
    if retain_days != -1 and retain_days < 30:
        raise ValueError("retain_days must be at least 30 or -1 for indefinite")
    if action not in {"anonymise", "delete"}:
        raise ValueError("action must be anonymise or delete")
    policies = {row["data_category"]: row for row in get_retention_policies()}
    row = {
        "data_category": data_category,
        "retain_days": retain_days,
        "action": action,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    policies[data_category] = row
    path = _privacy_dir() / "retention_policies.json"
    path.write_text(json.dumps(list(policies.values()), indent=2), encoding="utf-8")
    return row


def get_last_retention_run() -> str | None:
    return _last_retention_run


def retention_cutoff(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


async def apply_retention_policies() -> dict[str, Any]:
    """Purge expired research tasks and old DSAR export files."""
    results: dict[str, int] = {"research_purged": 0, "dsar_exports_removed": 0}

    try:
        from keprix.research.registry import get_research_registry

        results["research_purged"] = get_research_registry().purge_expired()
    except Exception:
        pass

    try:
        from keprix.privacy.dsar import _privacy_dir

        export_dir = _privacy_dir() / "exports"
        cutoff = retention_cutoff(DEFAULT_RETENTION_DAYS["dsar_exports"])
        if export_dir.exists():
            for path in export_dir.glob("dsar-*.json"):
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                if mtime < cutoff:
                    path.unlink(missing_ok=True)
                    results["dsar_exports_removed"] += 1
    except Exception:
        pass

    global _last_retention_run
    _last_retention_run = datetime.now(timezone.utc).isoformat()
    return results
