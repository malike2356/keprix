"""Bootstrap Customer Concierge stores (Prompt 628)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def ensure_concierge_tables() -> list[str]:
    names: list[str] = []
    try:
        from keprix.customer_concierge.prompt_overlay import ensure_prompt_layer_registered
        from keprix.customer_concierge.store import get_concierge_store

        get_concierge_store()
        ensure_prompt_layer_registered()
        names.append("sqlite:customer_concierge")
    except Exception:
        logger.exception("customer concierge sqlite bootstrap failed")

    try:
        from sqlalchemy import text

        from keprix.database import get_engine

        engine = get_engine()
        if engine is None:
            return names
        ddl = """
        CREATE TABLE IF NOT EXISTS concierge_profiles (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            persona_id TEXT NOT NULL,
            published BOOLEAN NOT NULL DEFAULT false,
            published_at TIMESTAMPTZ,
            persona_name TEXT,
            greeting_message TEXT,
            business_name TEXT,
            business_description TEXT,
            knowledge_source_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
            meeting_type_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
            channel_config JSONB NOT NULL DEFAULT '{}'::jsonb,
            calendar_provider TEXT,
            calendar_connected BOOLEAN NOT NULL DEFAULT false,
            conferencing_provider TEXT,
            conferencing_connected BOOLEAN NOT NULL DEFAULT false,
            business_hours JSONB,
            escalation_email TEXT,
            ics_fallback_ok BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(workspace_id, persona_id)
        );
        CREATE INDEX IF NOT EXISTS idx_concierge_profiles_workspace
            ON concierge_profiles (workspace_id);
        CREATE INDEX IF NOT EXISTS idx_concierge_profiles_published
            ON concierge_profiles (workspace_id, published)
            WHERE published = true;
        CREATE TABLE IF NOT EXISTS concierge_widget_sessions (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            persona_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            closed_at TIMESTAMPTZ
        );
        """
        async with engine.begin() as conn:
            for stmt in ddl.split(";"):
                chunk = stmt.strip()
                if chunk:
                    await conn.execute(text(chunk))
        names.extend(["concierge_profiles", "concierge_widget_sessions"])
        logger.info("customer concierge postgres tables verified")
    except Exception:
        logger.exception("customer concierge postgres bootstrap failed")
    return names
