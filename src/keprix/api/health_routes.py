"""Health and status endpoints."""

from __future__ import annotations

import os
import time

from fastapi import APIRouter, Depends

from keprix.api.auth import require_admin
from keprix.config.constants import EDITION, PRODUCT_NAME, PRODUCT_VERSION

router = APIRouter(tags=["health"])
_START_TIME = time.time()


@router.get("/api/health")
async def basic_health() -> dict[str, str]:
    return {"status": "ok", "product": PRODUCT_NAME, "version": PRODUCT_VERSION, "edition": EDITION}


@router.get("/api/v1/health")
async def basic_health_v1() -> dict[str, str]:
    return await basic_health()


@router.get("/api/health/detailed")
async def detailed_health(_admin: str = Depends(require_admin)) -> dict:
    from keprix.config.health_monitor import ConfigHealthMonitor

    monitor = ConfigHealthMonitor()
    await monitor._run_all_checks()
    checks = monitor.get_all()

    database = {"connected": False, "version": "", "pgvector": False}
    redis_status = {"connected": False}
    providers: list[dict] = []
    gateway = {"running": False, "channels": []}
    cron_status = {"active_jobs": 0, "next_run_at": ""}

    for name, health in checks.items():
        if name == "postgres":
            database["connected"] = health.status == "healthy"
        elif name == "redis":
            redis_status["connected"] = health.status == "healthy"
        elif name.startswith("llm:"):
            providers.append(
                {
                    "name": name.removeprefix("llm:"),
                    "configured": True,
                    "healthy": health.status == "healthy",
                    "model_count": 0,
                }
            )
        elif name.startswith("channel:"):
            gateway["channels"].append(
                {
                    "name": name.removeprefix("channel:"),
                    "connected": health.status == "healthy",
                }
            )

    try:
        from gateway.status import get_running_pid
        from keprix_cli.config import get_keprix_home

        pid_path = get_keprix_home() / "gateway.pid"
        gateway["running"] = get_running_pid(pid_path, cleanup_stale=False) is not None
    except Exception:
        pass

    try:
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        root_str = str(root)
        if root_str not in sys.path:
            sys.path.insert(0, root_str)
        from cron import jobs as cron_jobs

        jobs = cron_jobs.list_jobs(include_disabled=True)
        enabled = [job for job in jobs if job.get("enabled", True)]
        cron_status["active_jobs"] = len(enabled)
        if enabled:
            cron_status["next_run_at"] = str(enabled[0].get("next_run_at") or "")
    except Exception:
        pass

    searxng_url = os.environ.get("KEPRIX_SEARXNG_URL", "http://localhost:8080")
    searxng = {"available": False, "url": searxng_url}
    try:
        import httpx

        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{searxng_url.rstrip('/')}/healthz")
            searxng["available"] = response.status_code < 500
    except Exception:
        pass

    return {
        "database": database,
        "redis": redis_status,
        "searxng": searxng,
        "providers": providers,
        "gateway": gateway,
        "cron": cron_status,
        "version": PRODUCT_VERSION,
        "uptime_seconds": int(time.time() - _START_TIME),
    }
