"""Ensure CRM sqlite (and optional future Postgres) tables exist on API startup."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def ensure_crm_tables() -> list[str]:
    """Warm the CRM sqlite store so schema exists. Never drops data."""
    names: list[str] = []
    try:
        from keprix.crm.store import get_crm_store

        store = get_crm_store()
        # Touch a workspace-scoped list to prove schema is readable.
        store.list_accounts("__bootstrap__", limit=1)
        names.append("sqlite:crm")
        logger.info("crm sqlite tables verified")
    except Exception:
        logger.exception("crm sqlite bootstrap failed")
    return names
