"""System diagnostics endpoints."""

from __future__ import annotations

import os
import shutil
from typing import Any

from fastapi import APIRouter, Depends

from keprix.api.auth import require_admin

router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])


async def _run_checks() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    async def add(name: str, passed: bool, detail: str = "") -> None:
        results.append({"name": name, "status": "pass" if passed else "fail", "detail": detail})

    try:
        from keprix.db.postgres import ping

        await ping()
        await add("database", True, "PostgreSQL reachable")
    except Exception as exc:
        await add("database", False, str(exc)[:200])

    try:
        from keprix.db.redis_client import get_redis
        import asyncio

        client = await get_redis()
        await asyncio.to_thread(client.ping)
        await add("redis", True, "Redis ping OK")
    except Exception as exc:
        await add("redis", False, str(exc)[:200])

    searxng_url = os.environ.get("KEPRIX_SEARXNG_URL", "http://localhost:8080")
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{searxng_url.rstrip('/')}/healthz")
            await add("searxng", response.status_code < 500, f"HTTP {response.status_code}")
    except Exception as exc:
        await add("searxng", False, str(exc)[:200])

    try:
        from keprix.brain.provider_registry import iter_configured_providers

        providers = iter_configured_providers()
        await add("llm_providers", bool(providers), f"{len(providers)} provider(s) configured")
    except Exception as exc:
        await add("llm_providers", False, str(exc)[:200])

    usage = shutil.disk_usage("/")
    free_gb = usage.free / (1024**3)
    await add("disk_space", free_gb > 1.0, f"{free_gb:.1f} GB free")

    try:
        import psutil

        mem = psutil.virtual_memory()
        await add("memory", mem.available > 256 * 1024 * 1024, f"{mem.available // (1024**2)} MB available")
    except Exception as exc:
        await add("memory", True, f"psutil unavailable: {exc}")

    try:
        from keprix.email.store import get_email_store
        from keprix.email.helpers import test_imap_smtp
        import asyncio

        accounts = await get_email_store().list_active_accounts()
        if not accounts:
            await add("imap", True, "No IMAP account configured")
        else:
            account = accounts[0]
            ok = await asyncio.to_thread(test_imap_smtp, account.to_connection())
            await add(
                "imap",
                bool(ok),
                account.email_address or account.imap_host or "configured account",
            )
    except Exception as exc:
        await add("imap", False, str(exc)[:200])

    return results


@router.get("")
async def diagnostics(_admin: str = Depends(require_admin)) -> dict:
    checks = await _run_checks()
    return {
        "checks": checks,
        "passed": sum(1 for check in checks if check["status"] == "pass"),
        "failed": sum(1 for check in checks if check["status"] == "fail"),
    }


@router.post("/run")
async def run_diagnostics(_admin: str = Depends(require_admin)) -> dict:
    checks = await _run_checks()
    return {"checks": checks, "ran_at": __import__("time").time()}
