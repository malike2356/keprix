"""Alembic: Document Vault search index and job lifecycle (Prompt 652)."""

from __future__ import annotations

from alembic import op

revision = "032_document_vault_search_ops"
down_revision = "031_document_vault_channel_ops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_vault_index_entries (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            revision INTEGER NOT NULL,
            source_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            chunk_count INTEGER NOT NULL DEFAULT 0,
            content_checksum TEXT,
            indexed_at TEXT,
            error TEXT,
            UNIQUE(workspace_id, item_id, revision)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_dv_index_ws_item
            ON document_vault_index_entries(workspace_id, item_id)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_vault_index_chunks (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            revision INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            UNIQUE(workspace_id, item_id, revision, chunk_index)
        )
        """
    )
    for col, ddl in (
        ("retry_count", "INTEGER NOT NULL DEFAULT 0"),
        ("max_retries", "INTEGER NOT NULL DEFAULT 3"),
        ("dead_letter_reason", "TEXT"),
        ("claimed_by", "TEXT"),
        ("claimed_at", "TEXT"),
    ):
        try:
            op.execute(f"ALTER TABLE document_vault_jobs ADD COLUMN {col} {ddl}")
        except Exception:
            pass


def downgrade() -> None:
    pass
