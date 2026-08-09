"""Seed Keprix cron jobs for outreach automation (K02)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

OUTREACH_CRON_JOBS: tuple[dict[str, Any], ...] = (
    {
        "name": "outreach-process-due",
        "schedule": "every 5m",
        "prompt": (
            "Run outreach_process_due for active workspaces using the durable "
            "claim-lease campaign scheduler. Process due sequence steps "
            "(Soft Wall park or dry-run as configured). "
            "Summarize processed, skipped, claimed, and dead-letter counts."
        ),
        "enabled_toolsets": ["outreach"],
    },
    {
        "name": "outreach-scan-replies",
        "schedule": "every 2m",
        "prompt": (
            "Call the outreach_scan_replies tool for active workspaces. "
            "It polls bound email accounts, matches inbound mail to outbound "
            "deliveries, classifies matched replies, parks ambiguous items for "
            "review, and advances mailbox cursors. Summarize scanned, matched, "
            "ambiguous, unmatched, and deduped counts. Do not invent replies."
        ),
        "enabled_toolsets": ["outreach"],
    },
    {
        "name": "outreach-daily-digest",
        "schedule": "0 8 * * *",
        "prompt": (
            "Produce the daily outreach digest for each active workspace: new leads, "
            "replies, and bookings. Deliver a short summary to the workspace owner."
        ),
        "enabled_toolsets": ["outreach"],
    },
    {
        "name": "outreach-delivery-reconcile",
        "schedule": "0 4 * * *",
        "prompt": (
            "Run outreach delivery reconciliation: flag stuck sent/accepted "
            "messages without delivered/bounce events, expire stale Soft Wall "
            "approvals, and summarize dry_run / not_configured / drift counts. "
            "Do not auto-resend; Soft Wall remains the cold-send gate."
        ),
        "enabled_toolsets": ["outreach"],
    },
)


def ensure_outreach_cron_jobs() -> list[dict[str, Any]]:
    """Idempotently create outreach cron jobs."""
    try:
        from cron.jobs import create_job, list_jobs
    except Exception:
        try:
            from keprix.cron.jobs import create_job, list_jobs  # type: ignore
        except Exception as exc:
            logger.warning("outreach cron seed skipped: %s", exc)
            return []

    existing_names = {str(j.get("name") or "") for j in list_jobs()}
    created: list[dict[str, Any]] = []
    for spec in OUTREACH_CRON_JOBS:
        name = str(spec["name"])
        if name in existing_names:
            continue
        try:
            job = create_job(
                prompt=str(spec["prompt"]),
                schedule=str(spec["schedule"]),
                name=name,
                enabled_toolsets=list(spec.get("enabled_toolsets") or ["outreach"]),
                deliver="local",
            )
            created.append(job)
            logger.info("seeded outreach cron job %s", name)
        except Exception:
            logger.exception("failed to seed cron job %s", name)
    return created
