"""Alembic: Document Vault channel bindings and delivery tokens (Prompt 651)."""

from __future__ import annotations

from alembic import op

revision = "031_document_vault_channel_ops"
down_revision = "030_document_vault_google_drive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_vault_channel_bindings (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            channel_user_id TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            audience TEXT NOT NULL DEFAULT 'private',
            grants_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(platform, channel_user_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_dv_channel_bindings_ws
            ON document_vault_channel_bindings(workspace_id, status)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_vault_channel_events (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            event_id TEXT NOT NULL,
            action TEXT NOT NULL,
            result_item_id TEXT,
            result_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            UNIQUE(workspace_id, platform, event_id, action)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_dv_channel_events_ws
            ON document_vault_channel_events(workspace_id, created_at)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_vault_delivery_tokens (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_by TEXT,
            created_at TEXT NOT NULL,
            consumed_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_dv_delivery_tokens_hash
            ON document_vault_delivery_tokens(token_hash)
        """
    )


def downgrade() -> None:
    pass
