"""Ensure worker KB local store is warm (Postgres via Alembic)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def ensure_worker_kb_tables() -> list[str]:
    names: list[str] = []
    try:
        from keprix.worker_kb.store import get_worker_kb_store

        get_worker_kb_store()
        names.append("sqlite:worker_kb")
    except Exception:
        logger.exception("worker kb sqlite bootstrap failed")

    try:
        from keprix.database import get_engine
        from sqlalchemy import text

        engine = get_engine()
        if engine is None:
            return names
        ddl = """
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
        CREATE TABLE IF NOT EXISTS worker_knowledge_bases (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id TEXT NOT NULL,
            worker_id TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT 'Default',
            created_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE(workspace_id, worker_id, name)
        );
        CREATE TABLE IF NOT EXISTS worker_knowledge_entries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            knowledge_base_id UUID REFERENCES worker_knowledge_bases(id) ON DELETE CASCADE,
            entry_type TEXT NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            source TEXT,
            source_file TEXT,
            token_count INTEGER,
            enabled BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
        """
        async with engine.begin() as conn:
            for stmt in ddl.split(";"):
                chunk = stmt.strip()
                if chunk:
                    await conn.execute(text(chunk))
        names.extend(["worker_knowledge_bases", "worker_knowledge_entries"])
        logger.info("worker kb postgres tables verified")
    except Exception:
        logger.exception("worker kb postgres bootstrap failed")
    return names
