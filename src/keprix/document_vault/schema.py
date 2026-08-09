"""SQLite / Postgres-compatible DDL for Document Vault (Prompt 646)."""

from __future__ import annotations

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS document_vault_items (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    parent_id TEXT,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    extension TEXT NOT NULL DEFAULT '',
    content_authority TEXT NOT NULL DEFAULT 'workspace',
    storage_locator TEXT,
    byte_size INTEGER NOT NULL DEFAULT 0,
    checksum TEXT,
    current_revision INTEGER NOT NULL DEFAULT 0,
    created_by TEXT,
    updated_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    trashed_at TEXT,
    trash_parent_id TEXT,
    index_policy TEXT NOT NULL DEFAULT 'inherit',
    classification TEXT NOT NULL DEFAULT 'internal',
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS ix_dv_items_ws_parent
    ON document_vault_items(workspace_id, parent_id);
CREATE INDEX IF NOT EXISTS ix_dv_items_ws_trash
    ON document_vault_items(workspace_id, trashed_at);
CREATE INDEX IF NOT EXISTS ix_dv_items_ws_name
    ON document_vault_items(workspace_id, name);

CREATE TABLE IF NOT EXISTS document_vault_revisions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    storage_locator TEXT,
    byte_size INTEGER NOT NULL DEFAULT 0,
    checksum TEXT,
    change_summary TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(workspace_id, item_id, revision)
);

CREATE INDEX IF NOT EXISTS ix_dv_revisions_item
    ON document_vault_revisions(workspace_id, item_id);

CREATE TABLE IF NOT EXISTS document_vault_audit (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    item_id TEXT,
    action TEXT NOT NULL,
    actor_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_dv_audit_ws
    ON document_vault_audit(workspace_id, created_at);

CREATE TABLE IF NOT EXISTS document_vault_jobs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    item_id TEXT,
    idempotency_key TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS ix_dv_jobs_ws_status
    ON document_vault_jobs(workspace_id, status);

CREATE TABLE IF NOT EXISTS document_vault_provider_mappings (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_item_id TEXT NOT NULL,
    provider_revision TEXT,
    content_authority TEXT NOT NULL DEFAULT 'google',
    last_synced_at TEXT,
    conflict_state TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(workspace_id, provider, provider_item_id)
);

CREATE TABLE IF NOT EXISTS document_vault_source_mappings (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    source_store TEXT NOT NULL,
    source_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    checksum TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(workspace_id, idempotency_key),
    UNIQUE(workspace_id, source_store, source_id)
);
"""

# Postgres uses the same TEXT schema (CRM-style) so domain SQL stays portable.
PG_SCHEMA = SQLITE_SCHEMA
