"""Bootstrap Customer Concierge stores (Prompt 628)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def ensure_concierge_tables() -> list[str]:
    names: list[str] = []
    try:
        from keprix.customer_concierge.audience.store import get_audience_store
        from keprix.customer_concierge.prompt_overlay import ensure_prompt_layer_registered
        from keprix.customer_concierge.store import get_concierge_store

        get_concierge_store()
        get_audience_store()
        ensure_prompt_layer_registered()
        names.append("sqlite:customer_concierge")
        names.append("sqlite:audience_principal")
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
        CREATE TABLE IF NOT EXISTS audience_identities (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            external_key TEXT NOT NULL,
            display_name TEXT,
            email TEXT,
            phone TEXT,
            crm_contact_id TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(workspace_id, channel, external_key)
        );
        CREATE TABLE IF NOT EXISTS audience_sessions (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            persona_id TEXT NOT NULL,
            concierge_profile_id TEXT,
            identity_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            session_mode TEXT NOT NULL DEFAULT 'public',
            widget_session_token TEXT,
            origin TEXT,
            locale TEXT,
            consent_state TEXT NOT NULL DEFAULT 'unknown',
            risk_state TEXT NOT NULL DEFAULT 'normal',
            status TEXT NOT NULL DEFAULT 'active',
            expires_at TIMESTAMPTZ NOT NULL,
            last_active_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_audience_sessions_ws
            ON audience_sessions (workspace_id, persona_id);
        CREATE INDEX IF NOT EXISTS idx_audience_sessions_token
            ON audience_sessions (widget_session_token);
        CREATE TABLE IF NOT EXISTS audience_rate_buckets (
            bucket_key TEXT PRIMARY KEY,
            hit_count INTEGER NOT NULL DEFAULT 0,
            reset_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS audience_embed_nonces (
            nonce TEXT PRIMARY KEY,
            persona_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            consumed_at TIMESTAMPTZ
        );
        CREATE TABLE IF NOT EXISTS audience_audit_events (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            session_id TEXT,
            identity_id TEXT,
            event_type TEXT NOT NULL,
            actor_type TEXT NOT NULL DEFAULT 'system',
            detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_audience_audit_ws
            ON audience_audit_events (workspace_id, created_at);
        """
        async with engine.begin() as conn:
            for stmt in ddl.split(";"):
                chunk = stmt.strip()
                if chunk:
                    await conn.execute(text(chunk))
        names.extend(
            [
                "concierge_profiles",
                "concierge_widget_sessions",
                "audience_identities",
                "audience_sessions",
                "audience_rate_buckets",
                "audience_embed_nonces",
                "audience_audit_events",
            ]
        )
        logger.info("customer concierge postgres tables verified")
    except Exception:
        logger.exception("customer concierge postgres bootstrap failed")
    return names
