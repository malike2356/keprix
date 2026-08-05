"""Ensure contacts Postgres tables exist (safe checkfirst create)."""

from __future__ import annotations

import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)


async def ensure_contacts_tables() -> list[str]:
    """Create contacts* tables if missing. Never drops data."""
    try:
        from keprix.database import Base, get_engine
        from keprix.db.models import (
            ContactActionPreferencesRow,
            ContactRow,
            ContactSyncSourceRow,
            VaultItemRow,
        )
    except Exception:
        logger.exception("contacts bootstrap import failed")
        return []

    engine = get_engine()
    if engine is None:
        logger.warning("contacts bootstrap skipped: no database engine")
        return []

    tables = [
        VaultItemRow.__table__,
        ContactRow.__table__,
        ContactSyncSourceRow.__table__,
        ContactActionPreferencesRow.__table__,
    ]
    try:
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables, checkfirst=True)
            )
            # Harden older empty schemas that may lack user_id.
            await conn.execute(
                text(
                    """
                    DO $$
                    BEGIN
                      IF EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_name = 'contacts'
                      ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'contacts' AND column_name = 'user_id'
                      ) THEN
                        ALTER TABLE contacts ADD COLUMN user_id TEXT NOT NULL DEFAULT 'local';
                      END IF;
                      IF EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_name = 'contact_sync_sources'
                      ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'contact_sync_sources' AND column_name = 'user_id'
                      ) THEN
                        ALTER TABLE contact_sync_sources
                          ADD COLUMN user_id TEXT NOT NULL DEFAULT 'local';
                      END IF;
                    END $$;
                    """
                )
            )
        names = [table.name for table in tables]
        logger.info("contacts tables verified: %s", ", ".join(names))
        return names
    except Exception:
        logger.exception("contacts bootstrap create_all failed")
        return []
