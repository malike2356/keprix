"""Backup operations with timeout, progress, and failure reasons."""

from __future__ import annotations

import concurrent.futures
import logging
import os
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

DEFAULT_BACKUP_TIMEOUT_SEC = 120


class BackupTimedOut(RuntimeError):
    def __init__(self, timeout_sec: float) -> None:
        super().__init__(f"Backup timed out after {timeout_sec:.0f}s")
        self.timeout_sec = timeout_sec


def backup_timeout_sec() -> float:
    try:
        return max(5.0, float(os.environ.get("KEPRIX_BACKUP_TIMEOUT_SEC") or DEFAULT_BACKUP_TIMEOUT_SEC))
    except ValueError:
        return float(DEFAULT_BACKUP_TIMEOUT_SEC)


def run_backup_with_timeout(
    create_fn: Callable[[], dict[str, Any]],
    *,
    timeout_sec: float | None = None,
) -> dict[str, Any]:
    """Run backup creation with a hard timeout; never hang the upgrade/readiness path."""
    limit = timeout_sec if timeout_sec is not None else backup_timeout_sec()
    started = time.perf_counter()
    progress: dict[str, Any] = {"phase": "starting", "started_at": started}
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(create_fn)
        try:
            progress["phase"] = "running"
            result = future.result(timeout=limit)
            progress["phase"] = "done"
            result = dict(result)
            result["progress"] = {
                **progress,
                "elapsed_sec": round(time.perf_counter() - started, 3),
                "timeout_sec": limit,
            }
            result["ok"] = True
            return result
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            raise BackupTimedOut(limit) from exc
        except Exception as exc:
            logger.exception("backup failed")
            return {
                "ok": False,
                "error": str(exc),
                "failure_reason": str(exc),
                "progress": {
                    **progress,
                    "phase": "failed",
                    "elapsed_sec": round(time.perf_counter() - started, 3),
                    "timeout_sec": limit,
                },
            }


def create_backup_safe(*, password: str | None = None, timeout_sec: float | None = None) -> dict[str, Any]:
    from keprix.workspace.backup_service import backup_service

    def _create() -> dict[str, Any]:
        return backup_service.create_backup(password=password)

    try:
        return run_backup_with_timeout(_create, timeout_sec=timeout_sec)
    except BackupTimedOut as exc:
        return {
            "ok": False,
            "error": str(exc),
            "failure_reason": "timeout",
            "timeout_sec": exc.timeout_sec,
            "recovery_message": (
                "Backup did not finish in time. Check disk space and KEPRIX_HOME size, "
                "then retry with a longer KEPRIX_BACKUP_TIMEOUT_SEC or exclude large caches."
            ),
        }
