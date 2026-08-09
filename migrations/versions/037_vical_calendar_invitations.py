"""Alembic: viCal calendar projections, delivery, watches, outbox (Prompt 633)."""

from __future__ import annotations

from alembic import op

revision = "037_vical_calendar_invitations"
down_revision = "036_vical_booking_saga_zoom"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vical_calendar_projections (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            booking_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            provider_event_id TEXT,
            etag TEXT,
            html_link TEXT,
            host_event_created BOOLEAN NOT NULL DEFAULT false,
            invitation_send_requested BOOLEAN NOT NULL DEFAULT false,
            invitation_delivery_state TEXT NOT NULL DEFAULT 'unknown',
            attendees_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            workspace_event_id TEXT,
            ics_uid TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            detail TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(workspace_id, booking_id, provider)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vical_delivery_attempts (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            booking_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            provider TEXT NOT NULL,
            status TEXT NOT NULL,
            evidence TEXT,
            detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vical_calendar_watch_channels (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            resource_id TEXT,
            expiration_at TIMESTAMPTZ NOT NULL,
            sync_token TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(workspace_id, provider, channel_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vical_notification_outbox (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            booking_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            to_address TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            evidence TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            delivered_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_vical_proj_booking
            ON vical_calendar_projections(workspace_id, booking_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_vical_outbox_status
            ON vical_notification_outbox(status, created_at)
        """
    )


def downgrade() -> None:
    pass
