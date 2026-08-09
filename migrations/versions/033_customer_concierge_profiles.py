"""Alembic: Customer Concierge profiles (Prompt 628)."""

from __future__ import annotations

from alembic import op

revision = "033_customer_concierge_profiles"
down_revision = "032_document_vault_search_ops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
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
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_concierge_profiles_workspace
            ON concierge_profiles (workspace_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_concierge_profiles_published
            ON concierge_profiles (workspace_id, published)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS concierge_widget_sessions (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            persona_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            closed_at TIMESTAMPTZ
        )
        """
    )


def downgrade() -> None:
    pass
