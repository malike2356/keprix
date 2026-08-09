"""Alembic: published knowledge + customer support cases (Prompt 631)."""

from __future__ import annotations

from alembic import op

revision = "035_published_knowledge_support"
down_revision = "034_audience_principal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE audience_sessions
            ADD COLUMN IF NOT EXISTS active_support_case_id TEXT
        """
    )
    op.execute(
        """
        ALTER TABLE audience_sessions
            ADD COLUMN IF NOT EXISTS handed_off_at TIMESTAMPTZ
        """
    )
    op.execute(
        """
        ALTER TABLE audience_sessions
            ADD COLUMN IF NOT EXISTS operator_user_id TEXT
        """
    )
    op.execute(
        """
        ALTER TABLE audience_sessions
            ADD COLUMN IF NOT EXISTS conversation_summary TEXT
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS concierge_knowledge_sources (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            persona_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            source_type TEXT NOT NULL DEFAULT 'faq',
            publish_state TEXT NOT NULL DEFAULT 'draft',
            revision INTEGER NOT NULL DEFAULT 1,
            enabled BOOLEAN NOT NULL DEFAULT true,
            language TEXT NOT NULL DEFAULT 'en',
            published_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_concierge_knowledge_ws
            ON concierge_knowledge_sources (workspace_id, persona_id, publish_state)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS concierge_knowledge_revisions (
            id TEXT PRIMARY KEY,
            entry_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            persona_id TEXT NOT NULL,
            revision INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            publish_state TEXT NOT NULL,
            created_by TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(entry_id, revision)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS concierge_support_cases (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            persona_id TEXT NOT NULL,
            concierge_profile_id TEXT,
            audience_session_id TEXT,
            identity_id TEXT,
            contact_id TEXT,
            channel TEXT NOT NULL DEFAULT 'web',
            subject TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            priority TEXT NOT NULL DEFAULT 'normal',
            assignee_user_id TEXT,
            sla_first_response_at TIMESTAMPTZ,
            sla_resolution_at TIMESTAMPTZ,
            first_responded_at TIMESTAMPTZ,
            resolved_at TIMESTAMPTZ,
            conversation_summary TEXT,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            scope TEXT NOT NULL DEFAULT 'tenant_customer_support',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_concierge_cases_ws
            ON concierge_support_cases (workspace_id, persona_id, status)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS concierge_support_case_events (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            actor_type TEXT NOT NULL DEFAULT 'system',
            actor_id TEXT,
            detail TEXT,
            payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS concierge_internal_notes (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            persona_id TEXT NOT NULL,
            case_id TEXT,
            audience_session_id TEXT,
            author_user_id TEXT,
            body TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS concierge_conversation_messages (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            persona_id TEXT NOT NULL,
            audience_session_id TEXT NOT NULL,
            case_id TEXT,
            role TEXT NOT NULL,
            body TEXT NOT NULL,
            citations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )


def downgrade() -> None:
    pass
