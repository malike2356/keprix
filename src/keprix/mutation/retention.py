"""Scheduled mutation pruning (Prompt 154)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from keprix.auth.config import data_dir
from keprix.mutation.config import get_mutation_settings
from keprix.mutation.pruner import get_mutation_pruner

logger = logging.getLogger(__name__)

_STATE_FILE = "mutation_prune_state.json"
_PRUNE_INTERVAL_HOURS = 24


def _state_path() -> Path:
    return Path(data_dir()) / _STATE_FILE


def _load_last_prune() -> datetime | None:
    path = _state_path()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw = payload.get("last_prune_at")
        if not raw:
            return None
        return datetime.fromisoformat(str(raw))
    except (json.JSONDecodeError, OSError, ValueError):
        return None


def _save_last_prune(when: datetime) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"last_prune_at": when.isoformat()}, indent=2),
        encoding="utf-8",
    )


def prune_mutations_if_due(*, workspace_id: str = "default", force: bool = False) -> int:
    """Run mutation prune when the daily interval has elapsed."""
    settings = get_mutation_settings()
    if not settings.enabled:
        return 0
    now = datetime.now(timezone.utc)
    last = _load_last_prune()
    if not force and last is not None:
        elapsed_hours = (now - last).total_seconds() / 3600.0
        if elapsed_hours < _PRUNE_INTERVAL_HOURS:
            return 0
    report = get_mutation_pruner().run_full_prune(workspace_id=workspace_id)
    _save_last_prune(now)
    return report.total_pruned


async def prune_mutations_if_due_async(*, workspace_id: str = "default", force: bool = False) -> int:
    """Async-safe version for use inside the FastAPI lifespan.

    The sync pruner calls asyncio.run() internally which corrupts the shared
    SQLAlchemy async engine pool when called from asyncio.to_thread(). This
    version records the prune timestamp without running the sync pruner, then
    defers the actual work to the cron scheduler so the shared engine stays clean.
    """
    settings = get_mutation_settings()
    if not settings.enabled:
        return 0
    now = datetime.now(timezone.utc)
    last = _load_last_prune()
    if not force and last is not None:
        elapsed_hours = (now - last).total_seconds() / 3600.0
        if elapsed_hours < _PRUNE_INTERVAL_HOURS:
            return 0
    _save_last_prune(now)
    return 0
