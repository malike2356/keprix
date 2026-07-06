"""Retention for LLM usage events."""

from __future__ import annotations

import logging

from keprix.usage.config import get_llm_usage_config
from keprix.usage.store import get_llm_usage_store

logger = logging.getLogger(__name__)


def prune_llm_usage_events(*, retention_days: int | None = None) -> int:
    """Delete usage rows older than the retention window."""
    config = get_llm_usage_config()
    if not config.enabled:
        return 0
    days = retention_days or config.retention_days
    store = get_llm_usage_store()
    pruned = store.prune_sync(retention_days=days)
    if pruned:
        logger.info("Pruned %d llm usage events older than %d days", pruned, days)
    return pruned


async def prune_llm_usage_events_async(*, retention_days: int | None = None) -> int:
    config = get_llm_usage_config()
    if not config.enabled:
        return 0
    days = retention_days or config.retention_days
    return await get_llm_usage_store().prune_async(retention_days=days)
