"""Bootstrap Aiva analytics store (K04)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def ensure_analytics_tables() -> list[str]:
    names: list[str] = []
    try:
        from keprix.aiva_analytics.store import get_analytics_store

        get_analytics_store()
        names.append("sqlite:aiva_analytics")
    except Exception:
        logger.debug("analytics sqlite bootstrap skipped", exc_info=True)
    return names
