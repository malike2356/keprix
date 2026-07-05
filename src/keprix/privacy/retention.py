"""Data retention policy helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


DEFAULT_RETENTION_DAYS = {
    "research_jobs": 30,
    "audit_logs": 365,
    "dsar_exports": 30,
}

_last_retention_run: str | None = None


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
        from pathlib import Path

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
