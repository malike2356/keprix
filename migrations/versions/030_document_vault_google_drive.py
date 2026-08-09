"""Alembic: Document Vault Google Drive sync tables (Prompt 649)."""

from __future__ import annotations

from alembic import op

revision = "030_document_vault_google_drive"
down_revision = "029_document_vault"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_vault_drive_connections (
            workspace_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'two_way',
            root_folder_id TEXT,
            root_folder_name TEXT,
            vault_root_item_id TEXT,
            page_token TEXT,
            channel_id TEXT,
            resource_id TEXT,
            channel_expires_at TEXT,
            verification_token_hash TEXT NOT NULL DEFAULT '',
            grant_ciphertext TEXT,
            scopes_json TEXT NOT NULL DEFAULT '[]',
            account_email TEXT,
            shared_drives_enabled INTEGER NOT NULL DEFAULT 0,
            connected INTEGER NOT NULL DEFAULT 0,
            last_sync_at TEXT,
            last_error TEXT,
            updated_at TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_vault_drive_notifications (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            notification_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(workspace_id, notification_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_dv_drive_notifications_ws
            ON document_vault_drive_notifications(workspace_id, created_at)
        """
    )


def downgrade() -> None:
    pass
