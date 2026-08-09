"""Alembic: Customer Concierge audience principal (Prompt 630)."""

from __future__ import annotations

from alembic import op

revision = "034_audience_principal"
down_revision = "033_customer_concierge_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
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
        )
        """
    )
    op.execute(
        """
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
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_audience_sessions_ws
            ON audience_sessions (workspace_id, persona_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_audience_sessions_token
            ON audience_sessions (widget_session_token)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audience_rate_buckets (
            bucket_key TEXT PRIMARY KEY,
            hit_count INTEGER NOT NULL DEFAULT 0,
            reset_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audience_embed_nonces (
            nonce TEXT PRIMARY KEY,
            persona_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            consumed_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audience_audit_events (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            session_id TEXT,
            identity_id TEXT,
            event_type TEXT NOT NULL,
            actor_type TEXT NOT NULL DEFAULT 'system',
            detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_audience_audit_ws
            ON audience_audit_events (workspace_id, created_at)
        """
    )


def downgrade() -> None:
    pass
