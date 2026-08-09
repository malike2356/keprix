"""Ensure CRM sqlite (and Postgres when selected) tables exist on API startup."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def ensure_crm_tables() -> list[str]:
    """Warm the CRM store so schema exists. Never drops data."""
    names: list[str] = []
    try:
        from keprix.crm.store import get_crm_store

        store = get_crm_store()
        store.list_accounts("__bootstrap__", limit=1)
        names.append(f"{store.backend}:crm")
        logger.info("crm %s tables verified", store.backend)
    except Exception:
        logger.exception("crm bootstrap failed")

    try:
        from keprix.database import get_engine
        from sqlalchemy import text

        engine = get_engine()
        if engine is None:
            return names
        from keprix.crm.schema_pg import CRM_PG_SCHEMA_SQL

        async with engine.begin() as conn:
            for stmt in CRM_PG_SCHEMA_SQL.split(";"):
                chunk = stmt.strip()
                if not chunk:
                    continue
                await conn.execute(text(chunk))
        names.append("postgres:crm_schema")
        logger.info("crm postgres DDL verified")
    except Exception:
        logger.exception("crm postgres bootstrap failed")
    return names
