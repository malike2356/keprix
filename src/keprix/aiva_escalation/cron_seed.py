"""Seed cron for escalation timeout reassignment (K05)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

ESCALATION_CRON_JOBS: tuple[dict[str, Any], ...] = (
    {
        "name": "aiva-escalation-timeout",
        "schedule": "every 5m",
        "prompt": (
            "Call escalation_process_timeouts to reassign escalations that no human VA "
            "picked up within the configured timeout. Summarize reassigned count."
        ),
        "enabled_toolsets": ["escalation"],
    },
)


def ensure_escalation_cron_jobs() -> list[dict[str, Any]]:
    try:
        from cron.jobs import create_job, list_jobs
    except Exception:
        try:
            from keprix.cron.jobs import create_job, list_jobs  # type: ignore
        except Exception as exc:
            logger.warning("escalation cron seed skipped: %s", exc)
            return []

    existing = {str(j.get("name") or "") for j in list_jobs()}
    created: list[dict[str, Any]] = []
    for spec in ESCALATION_CRON_JOBS:
        name = str(spec["name"])
        if name in existing:
            continue
        try:
            job = create_job(
                prompt=str(spec["prompt"]),
                schedule=str(spec["schedule"]),
                name=name,
                enabled_toolsets=list(spec.get("enabled_toolsets") or ["escalation"]),
                deliver="local",
            )
            created.append(job)
        except Exception:
            logger.exception("failed to seed cron %s", name)
    return created
