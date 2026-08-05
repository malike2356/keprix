"""Ensure email Postgres tables exist (safe checkfirst create)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def ensure_email_tables() -> list[str]:
    """Create email_* and vault_items if missing. Never drops data."""
    try:
        from keprix.database import Base, get_engine
        from keprix.db.models import EmailAccountRow, EmailDraftRow, EmailRow, VaultItemRow
    except Exception:
        logger.exception("email bootstrap import failed")
        return []

    engine = get_engine()
    if engine is None:
        logger.warning("email bootstrap skipped: no database engine")
        return []

    tables = [
        VaultItemRow.__table__,
        EmailAccountRow.__table__,
        EmailRow.__table__,
        EmailDraftRow.__table__,
    ]
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables, checkfirst=True))
        names = [table.name for table in tables]
        logger.info("email tables verified: %s", ", ".join(names))
        return names
    except Exception:
        logger.exception("email bootstrap create_all failed")
        return []
