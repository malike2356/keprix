"""Ensure outreach tables exist (Postgres when available + local sqlite)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def ensure_outreach_tables() -> list[str]:
    """Create outreach_* TEXT tables on Postgres if engine is configured. Always warms store."""
    names: list[str] = []
    try:
        from keprix.outreach.store import get_outreach_store

        store = get_outreach_store()
        names.append(f"{store.backend}:outreach")
    except Exception:
        logger.exception("outreach store bootstrap failed")

    try:
        from keprix.database import get_engine
        from sqlalchemy import text

        engine = get_engine()
        if engine is None:
            return names
        from keprix.outreach.schema_pg import OUTREACH_PG_SCHEMA_SQL

        async with engine.begin() as conn:
            for stmt in OUTREACH_PG_SCHEMA_SQL.split(";"):
                chunk = stmt.strip()
                if not chunk:
                    continue
                await conn.execute(text(chunk))
        names.extend(
            [
                "outreach_campaigns",
                "outreach_sequences",
                "outreach_sequence_steps",
                "outreach_leads",
                "outreach_enrollments",
                "outreach_messages",
                "outreach_replies",
                "outreach_control",
                "outreach_lists",
                "outreach_list_members",
                "outreach_bookings",
                "outreach_approvals",
            ]
        )
        logger.info("outreach postgres TEXT tables verified")
    except Exception:
        logger.exception("outreach postgres bootstrap failed")
    return names
