"""Ensure Channel Shield Postgres tables exist (safe checkfirst create)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def ensure_channel_shield_tables() -> list[str]:
    """Create channel_shield_* tables if missing. Never drops data."""
    try:
        from keprix.channel_shield.models import (
            ChannelShieldAttachmentRow,
            ChannelShieldEventRow,
            ChannelShieldMessageRow,
            ChannelShieldProtectionRow,
        )
        from keprix.database import Base, get_engine
    except Exception:
        logger.exception("channel shield bootstrap import failed")
        return []

    engine = get_engine()
    if engine is None:
        logger.warning("channel shield bootstrap skipped: no database engine")
        return []

    tables = [
        ChannelShieldProtectionRow.__table__,
        ChannelShieldMessageRow.__table__,
        ChannelShieldAttachmentRow.__table__,
        ChannelShieldEventRow.__table__,
    ]
    try:
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: Base.metadata.create_all(
                    sync_conn, tables=tables, checkfirst=True
                )
            )
        names = [table.name for table in tables]
        logger.info("channel shield tables verified: %s", ", ".join(names))
        return names
    except Exception:
        logger.exception("channel shield bootstrap create_all failed")
        return []
