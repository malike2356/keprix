"""Safe diagnostics bundle generation."""

from __future__ import annotations

import os
import platform
import shutil
from typing import Any

from keprix.config.constants import PRODUCT_NAME, PRODUCT_VERSION
from keprix.security.redactor import get_redactor


async def _health_checks() -> list[dict[str, Any]]:
    from keprix.api.diagnostics_routes import _run_checks

    return await _run_checks()


def _enabled_modules() -> list[str]:
    modules: list[str] = ["core", "workspace", "vault"]
    if os.environ.get("KEPRIX_GOVERNANCE_ENABLED", "").lower() == "true":
        modules.append("governance")
    return modules


def _provider_status() -> list[dict[str, str]]:
    try:
        from keprix.brain.provider_registry import iter_configured_providers

        return [
            {"id": provider.name, "label": provider.name, "configured": "yes"}
            for provider in iter_configured_providers()
        ]
    except Exception:
        return []


def _config_summary() -> dict[str, str]:
    keys = [
        "AUTH_ENABLED",
        "KEPRIX_GOVERNANCE_ENABLED",
        "KEPRIX_DATA_DIR",
        "DATABASE_URL",
        "REDIS_URL",
    ]
    summary: dict[str, str] = {}
    redactor = get_redactor()
    for key in keys:
        value = os.environ.get(key, "")
        if not value:
            continue
        if any(token in key.lower() for token in ("password", "secret", "key", "token", "url")):
            summary[key] = "[configured]"
        else:
            summary[key] = redactor.redact(value)[:120]
    return summary


def _disk_usage() -> dict[str, float]:
    usage = shutil.disk_usage("/")
    return {
        "total_gb": round(usage.total / (1024**3), 2),
        "used_gb": round(usage.used / (1024**3), 2),
        "free_gb": round(usage.free / (1024**3), 2),
    }


def redact_bundle_text(text: str) -> str:
    return get_redactor().redact(text)


async def build_diagnostics_bundle(
    *,
    recent_errors: list[str] | None = None,
    job_failures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    redactor = get_redactor()
    errors = [redactor.redact(item) for item in (recent_errors or [])]
    failures = []
    for row in job_failures or []:
        failures.append({key: redactor.redact(str(value)) for key, value in row.items()})

    bundle = {
        "product": PRODUCT_NAME,
        "version": PRODUCT_VERSION,
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "enabled_modules": _enabled_modules(),
        "health_checks": await _health_checks(),
        "recent_redacted_errors": errors,
        "job_failures": failures,
        "provider_status": _provider_status(),
        "disk_usage": _disk_usage(),
        "config_summary": _config_summary(),
    }
    return bundle
