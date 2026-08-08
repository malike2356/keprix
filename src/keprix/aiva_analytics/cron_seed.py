"""Seed cron for Aiva analytics daily aggregate (K04)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

ANALYTICS_CRON_JOBS: tuple[dict[str, Any], ...] = (
    {
        "name": "aiva-analytics-daily-aggregate",
        "schedule": "0 8 * * *",
        "prompt": (
            "Call analytics_aggregate_daily to roll up yesterday's Aiva metrics "
            "into the daily summary table for faster dashboards. Report rows upserted."
        ),
        "enabled_toolsets": ["analytics"],
    },
)


def ensure_analytics_cron_jobs() -> list[dict[str, Any]]:
    try:
        from cron.jobs import create_job, list_jobs
    except Exception:
        try:
            from keprix.cron.jobs import create_job, list_jobs  # type: ignore
        except Exception as exc:
            logger.warning("analytics cron seed skipped: %s", exc)
            return []

    existing = {str(j.get("name") or "") for j in list_jobs()}
    created: list[dict[str, Any]] = []
    for spec in ANALYTICS_CRON_JOBS:
        name = str(spec["name"])
        if name in existing:
            continue
        try:
            job = create_job(
                prompt=str(spec["prompt"]),
                schedule=str(spec["schedule"]),
                name=name,
                enabled_toolsets=list(spec.get("enabled_toolsets") or ["analytics"]),
                deliver="local",
            )
            created.append(job)
            logger.info("seeded analytics cron job %s", name)
        except Exception:
            logger.exception("failed to seed cron %s", name)
    return created


def run_daily_aggregate() -> dict[str, Any]:
    from keprix.aiva_analytics.service import get_analytics_service

    return get_analytics_service().aggregate_daily(lookback_days=2)
