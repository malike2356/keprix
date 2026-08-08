"""Ensure Aiva escalation tables (sqlite + optional Postgres)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def ensure_escalation_tables() -> list[str]:
    names: list[str] = []
    try:
        from keprix.aiva_escalation.store import get_escalation_store

        get_escalation_store()
        names.append("sqlite:aiva_escalation")
    except Exception:
        logger.exception("aiva escalation sqlite bootstrap failed")

    try:
        from keprix.database import get_engine
        from sqlalchemy import text

        engine = get_engine()
        if engine is None:
            return names
        ddl = """
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
        CREATE TABLE IF NOT EXISTS aiva_escalations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id TEXT NOT NULL,
            worker_id TEXT NOT NULL,
            session_id TEXT,
            escalation_type TEXT NOT NULL,
            confidence_score REAL,
            original_input TEXT NOT NULL,
            holding_message TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            assigned_va TEXT,
            va_response TEXT,
            channel TEXT,
            notify_log TEXT,
            audit_log TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            assigned_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            reassigned_at TIMESTAMPTZ
        );
        CREATE TABLE IF NOT EXISTS aiva_human_assist_requests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id TEXT NOT NULL,
            worker_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            urgency TEXT NOT NULL DEFAULT 'normal',
            details TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            escalation_id UUID,
            created_at TIMESTAMPTZ DEFAULT now()
        );
        """
        async with engine.begin() as conn:
            for stmt in ddl.split(";"):
                chunk = stmt.strip()
                if chunk:
                    await conn.execute(text(chunk))
        names.extend(["aiva_escalations", "aiva_human_assist_requests"])
    except Exception:
        logger.exception("aiva escalation postgres bootstrap failed")
    return names
