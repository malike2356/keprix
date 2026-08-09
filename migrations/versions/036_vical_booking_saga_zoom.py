"""Alembic: viCal booking saga + Zoom artifacts (Prompt 632)."""

from __future__ import annotations

from alembic import op

revision = "036_vical_booking_saga_zoom"
down_revision = "035_published_knowledge_support"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vical_availability_holds (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            event_type_id TEXT,
            starts_at TIMESTAMPTZ NOT NULL,
            ends_at TIMESTAMPTZ NOT NULL,
            holder_token TEXT NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            status TEXT NOT NULL DEFAULT 'held',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vical_booking_intents (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            booking_id TEXT,
            guest_email TEXT NOT NULL,
            starts_at TIMESTAMPTZ NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(workspace_id, idempotency_key)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vical_booking_participants (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            booking_id TEXT NOT NULL,
            role TEXT NOT NULL,
            email TEXT,
            display_name TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vical_conference_artifacts (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            booking_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            meeting_id TEXT,
            join_url TEXT,
            host_start_url TEXT,
            passcode TEXT,
            managed BOOLEAN NOT NULL DEFAULT false,
            status TEXT NOT NULL,
            detail TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(workspace_id, booking_id, provider)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vical_provider_operations (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            booking_id TEXT,
            provider TEXT NOT NULL,
            operation TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            status TEXT NOT NULL,
            attempt INTEGER NOT NULL DEFAULT 1,
            request_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            response_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            error_code TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(workspace_id, provider, operation, idempotency_key)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vical_webhook_receipts (
            id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            event_id TEXT NOT NULL,
            event_type TEXT,
            payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(provider, event_id)
        )
        """
    )


def downgrade() -> None:
    pass
