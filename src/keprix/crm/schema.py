"""SQLite schema for workspace-scoped CRM (Soft Wall pattern)."""

from __future__ import annotations

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS crm_accounts (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    company_number TEXT,
    domain TEXT,
    emails TEXT NOT NULL DEFAULT '[]',
    phones TEXT NOT NULL DEFAULT '[]',
    source TEXT,
    domain_pack TEXT NOT NULL DEFAULT 'generic',
    stage TEXT NOT NULL DEFAULT 'discovered',
    scores TEXT NOT NULL DEFAULT '{}',
    tags TEXT NOT NULL DEFAULT '[]',
    assigned_agent TEXT,
    last_touch_at TEXT,
    external_source_id TEXT,
    actor_type TEXT,
    actor_id TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_leads (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    account_id TEXT,
    name TEXT,
    company_name TEXT,
    company_number TEXT,
    emails TEXT NOT NULL DEFAULT '[]',
    phones TEXT NOT NULL DEFAULT '[]',
    source TEXT,
    domain_pack TEXT NOT NULL DEFAULT 'generic',
    stage TEXT NOT NULL DEFAULT 'discovered',
    scores TEXT NOT NULL DEFAULT '{}',
    tags TEXT NOT NULL DEFAULT '[]',
    assigned_agent TEXT,
    last_touch_at TEXT,
    external_source_id TEXT,
    actor_type TEXT,
    actor_id TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    website TEXT,
    niche TEXT,
    locality TEXT,
    google_maps_url TEXT,
    google_reviews TEXT,
    google_rating TEXT,
    website_score TEXT,
    ranks_top3 TEXT,
    weakness TEXT,
    priority TEXT,
    notes TEXT,
    source_type TEXT,
    source_name TEXT,
    source_url TEXT,
    source_captured_at TEXT,
    source_job_id TEXT,
    owner_agent_id TEXT,
    owner_user_id TEXT,
    list_id TEXT,
    campaign_id TEXT,
    sequence_id TEXT,
    pipeline_stage TEXT,
    last_contacted_at TEXT,
    last_reply_at TEXT,
    next_action_at TEXT,
    consent_status TEXT,
    suppression_reason TEXT,
    custom_fields TEXT NOT NULL DEFAULT '{}',
    merged_at TEXT,
    converted_at TEXT,
    archived_at TEXT
);

CREATE TABLE IF NOT EXISTS crm_ingestion_jobs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    source_type TEXT,
    source_name TEXT,
    content_hash TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    created_count INTEGER NOT NULL DEFAULT 0,
    updated_count INTEGER NOT NULL DEFAULT 0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    warning_count INTEGER NOT NULL DEFAULT 0,
    actor_id TEXT,
    error_summary TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS crm_contacts (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    account_id TEXT,
    display_name TEXT NOT NULL,
    given_name TEXT,
    family_name TEXT,
    emails TEXT NOT NULL DEFAULT '[]',
    phones TEXT NOT NULL DEFAULT '[]',
    telegram_ids TEXT NOT NULL DEFAULT '[]',
    addresses TEXT NOT NULL DEFAULT '[]',
    source TEXT,
    domain_pack TEXT NOT NULL DEFAULT 'generic',
    stage TEXT NOT NULL DEFAULT 'discovered',
    scores TEXT NOT NULL DEFAULT '{}',
    tags TEXT NOT NULL DEFAULT '[]',
    assigned_agent TEXT,
    last_touch_at TEXT,
    external_source_id TEXT,
    contacts_module_id TEXT,
    actor_type TEXT,
    actor_id TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_deals (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    account_id TEXT,
    contact_id TEXT,
    lead_id TEXT,
    name TEXT NOT NULL,
    amount REAL,
    currency TEXT DEFAULT 'GBP',
    stage TEXT NOT NULL DEFAULT 'qualified',
    source TEXT,
    domain_pack TEXT NOT NULL DEFAULT 'generic',
    scores TEXT NOT NULL DEFAULT '{}',
    tags TEXT NOT NULL DEFAULT '[]',
    assigned_agent TEXT,
    last_touch_at TEXT,
    stripe_customer_id TEXT,
    external_source_id TEXT,
    actor_type TEXT,
    actor_id TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_activities (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    activity_type TEXT NOT NULL,
    channel TEXT,
    subject TEXT,
    body TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    actor_type TEXT,
    actor_id TEXT,
    occurred_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS crm_lists (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    stage TEXT NOT NULL DEFAULT 'listed',
    source TEXT,
    domain_pack TEXT NOT NULL DEFAULT 'generic',
    status TEXT NOT NULL DEFAULT 'draft',
    tags TEXT NOT NULL DEFAULT '[]',
    assigned_agent TEXT,
    last_touch_at TEXT,
    actor_type TEXT,
    actor_id TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_list_memberships (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    list_id TEXT NOT NULL,
    member_type TEXT NOT NULL,
    member_id TEXT NOT NULL,
    stage TEXT,
    created_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE(workspace_id, list_id, member_type, member_id)
);

CREATE TABLE IF NOT EXISTS crm_enrichment_jobs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed',
    sheet_type TEXT,
    source_path TEXT,
    output_path TEXT,
    domain_pack TEXT NOT NULL DEFAULT 'generic',
    proposal_json TEXT NOT NULL DEFAULT '{}',
    cells_filled INTEGER NOT NULL DEFAULT 0,
    cells_skipped INTEGER NOT NULL DEFAULT 0,
    cost_estimate REAL,
    error TEXT,
    actor_type TEXT,
    actor_id TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_consent_records (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    purpose TEXT NOT NULL,
    jurisdiction TEXT NOT NULL DEFAULT 'UK',
    lawful_basis TEXT NOT NULL,
    evidence TEXT,
    assessment_version TEXT,
    obtained_at TEXT,
    expires_at TEXT,
    withdrawn_at TEXT,
    actor_type TEXT,
    actor_id TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_suppression_entries (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    address TEXT NOT NULL,
    reason TEXT,
    source TEXT,
    subject_type TEXT,
    subject_id TEXT,
    actor_type TEXT,
    actor_id TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, channel, address)
);

CREATE TABLE IF NOT EXISTS crm_field_provenance (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    value_json TEXT,
    kind TEXT NOT NULL,
    source_url TEXT,
    source_record_id TEXT,
    adapter TEXT,
    evidence_excerpt TEXT,
    confidence REAL,
    verification_state TEXT,
    policy_version TEXT,
    observed_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_source_records (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    adapter TEXT NOT NULL,
    external_id TEXT,
    content_hash TEXT,
    snapshot_json TEXT NOT NULL DEFAULT '{}',
    retention_until TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_merge_suggestions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    left_id TEXT NOT NULL,
    right_id TEXT NOT NULL,
    match_keys TEXT NOT NULL DEFAULT '[]',
    score REAL,
    explanation TEXT,
    field_diff_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    soft_wall_approval_id TEXT,
    actor_type TEXT,
    actor_id TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_merge_history (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    suggestion_id TEXT,
    entity_type TEXT NOT NULL,
    survivor_id TEXT NOT NULL,
    merged_id TEXT NOT NULL,
    snapshot_json TEXT NOT NULL DEFAULT '{}',
    reversible INTEGER NOT NULL DEFAULT 1,
    reversed_at TEXT,
    actor_type TEXT,
    actor_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_discovery_jobs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    adapter TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    domain_pack TEXT NOT NULL DEFAULT 'generic',
    params_json TEXT NOT NULL DEFAULT '{}',
    result_counts_json TEXT NOT NULL DEFAULT '{}',
    cost_estimate REAL,
    list_id TEXT,
    error TEXT,
    checkpoint_json TEXT NOT NULL DEFAULT '{}',
    actor_type TEXT,
    actor_id TEXT,
    started_at TEXT,
    finished_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_outbox (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    idempotency_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    next_retry_at TEXT,
    correlation_id TEXT,
    entity_type TEXT,
    entity_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS crm_idempotency (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(workspace_id, scope, idempotency_key)
);

CREATE TABLE IF NOT EXISTS crm_contactability_decisions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    purpose TEXT NOT NULL,
    jurisdiction TEXT NOT NULL DEFAULT 'UK',
    decision TEXT NOT NULL,
    reason TEXT,
    policy_version TEXT,
    actor_type TEXT,
    actor_id TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, subject_type, subject_id, channel, purpose)
);

CREATE TABLE IF NOT EXISTS crm_sender_readiness (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    verified INTEGER NOT NULL DEFAULT 0,
    spf_ok INTEGER NOT NULL DEFAULT 0,
    dkim_ok INTEGER NOT NULL DEFAULT 0,
    dmarc_ok INTEGER NOT NULL DEFAULT 0,
    reply_mailbox TEXT,
    notes TEXT,
    actor_type TEXT,
    actor_id TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, domain)
);

CREATE TABLE IF NOT EXISTS crm_kill_switches (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    scope_id TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    reason TEXT,
    actor_type TEXT,
    actor_id TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, scope, scope_id)
);

CREATE INDEX IF NOT EXISTS ix_crm_accounts_ws ON crm_accounts(workspace_id, deleted_at);
CREATE INDEX IF NOT EXISTS ix_crm_accounts_email ON crm_accounts(workspace_id, company_number);
CREATE INDEX IF NOT EXISTS ix_crm_accounts_ext ON crm_accounts(workspace_id, external_source_id);
CREATE INDEX IF NOT EXISTS ix_crm_leads_ws ON crm_leads(workspace_id, deleted_at);
CREATE INDEX IF NOT EXISTS ix_crm_leads_ext ON crm_leads(workspace_id, external_source_id);
CREATE INDEX IF NOT EXISTS ix_crm_leads_ch ON crm_leads(workspace_id, company_number);
CREATE INDEX IF NOT EXISTS ix_crm_leads_website ON crm_leads(workspace_id, website);
CREATE INDEX IF NOT EXISTS ix_crm_ingestion_jobs_ws ON crm_ingestion_jobs(workspace_id, created_at);
CREATE INDEX IF NOT EXISTS ix_crm_contacts_ws ON crm_contacts(workspace_id, deleted_at);
CREATE INDEX IF NOT EXISTS ix_crm_contacts_ext ON crm_contacts(workspace_id, external_source_id);
CREATE INDEX IF NOT EXISTS ix_crm_deals_ws ON crm_deals(workspace_id, deleted_at);
CREATE INDEX IF NOT EXISTS ix_crm_lists_ws ON crm_lists(workspace_id, deleted_at);
CREATE INDEX IF NOT EXISTS ix_crm_memberships_list ON crm_list_memberships(workspace_id, list_id);
CREATE INDEX IF NOT EXISTS ix_crm_activities_entity ON crm_activities(workspace_id, entity_type, entity_id);
CREATE INDEX IF NOT EXISTS ix_crm_provenance_entity ON crm_field_provenance(workspace_id, entity_type, entity_id);
CREATE INDEX IF NOT EXISTS ix_crm_outbox_status ON crm_outbox(workspace_id, status);
CREATE INDEX IF NOT EXISTS ix_crm_merge_pending ON crm_merge_suggestions(workspace_id, status);
CREATE INDEX IF NOT EXISTS ix_crm_discovery_ws ON crm_discovery_jobs(workspace_id, status);
CREATE INDEX IF NOT EXISTS ix_crm_suppress_addr ON crm_suppression_entries(workspace_id, channel, address);
"""

# Additive lead columns for existing DBs (Prompt 621).
LEAD_INGESTION_COLUMNS: tuple[tuple[str, str], ...] = (
    ("website", "website TEXT"),
    ("niche", "niche TEXT"),
    ("locality", "locality TEXT"),
    ("google_maps_url", "google_maps_url TEXT"),
    ("google_reviews", "google_reviews TEXT"),
    ("google_rating", "google_rating TEXT"),
    ("website_score", "website_score TEXT"),
    ("ranks_top3", "ranks_top3 TEXT"),
    ("weakness", "weakness TEXT"),
    ("priority", "priority TEXT"),
    ("notes", "notes TEXT"),
    ("source_type", "source_type TEXT"),
    ("source_name", "source_name TEXT"),
    ("source_url", "source_url TEXT"),
    ("source_captured_at", "source_captured_at TEXT"),
    ("source_job_id", "source_job_id TEXT"),
    ("owner_agent_id", "owner_agent_id TEXT"),
    ("owner_user_id", "owner_user_id TEXT"),
    ("list_id", "list_id TEXT"),
    ("campaign_id", "campaign_id TEXT"),
    ("sequence_id", "sequence_id TEXT"),
    ("pipeline_stage", "pipeline_stage TEXT"),
    ("last_contacted_at", "last_contacted_at TEXT"),
    ("last_reply_at", "last_reply_at TEXT"),
    ("next_action_at", "next_action_at TEXT"),
    ("consent_status", "consent_status TEXT"),
    ("suppression_reason", "suppression_reason TEXT"),
    ("custom_fields", "custom_fields TEXT NOT NULL DEFAULT '{}'"),
    ("merged_at", "merged_at TEXT"),
    ("converted_at", "converted_at TEXT"),
    ("archived_at", "archived_at TEXT"),
)

INGESTION_JOBS_DDL = """
CREATE TABLE IF NOT EXISTS crm_ingestion_jobs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    source_type TEXT,
    source_name TEXT,
    content_hash TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    created_count INTEGER NOT NULL DEFAULT 0,
    updated_count INTEGER NOT NULL DEFAULT 0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    warning_count INTEGER NOT NULL DEFAULT 0,
    actor_id TEXT,
    error_summary TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ix_crm_ingestion_jobs_ws ON crm_ingestion_jobs(workspace_id, created_at);
CREATE INDEX IF NOT EXISTS ix_crm_leads_website ON crm_leads(workspace_id, website);
"""


def ensure_crm_lead_ingestion_columns(conn) -> None:
    """ADD COLUMN missing lead ingestion fields and ensure ingestion jobs table.

    Safe to call repeatedly. ``conn`` is a sqlite3 connection (or compatible).
    """
    conn.executescript(INGESTION_JOBS_DDL)
    existing = {row[1] for row in conn.execute("PRAGMA table_info(crm_leads)").fetchall()}
    for name, ddl in LEAD_INGESTION_COLUMNS:
        if name not in existing:
            # SQLite cannot ADD COLUMN with NOT NULL on existing tables without default
            # when rows exist; use nullable for alter path when DEFAULT is present.
            alter_ddl = ddl
            if name == "custom_fields" and "NOT NULL" in ddl:
                alter_ddl = "custom_fields TEXT DEFAULT '{}'"
            conn.execute(f"ALTER TABLE crm_leads ADD COLUMN {alter_ddl}")
    conn.commit()


SAVED_VIEWS_DDL = """
CREATE TABLE IF NOT EXISTS crm_saved_views (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    owner_user_id TEXT NOT NULL,
    visibility TEXT NOT NULL DEFAULT 'private',
    config_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_crm_saved_views_ws ON crm_saved_views(workspace_id, visibility);
CREATE INDEX IF NOT EXISTS ix_crm_saved_views_owner ON crm_saved_views(workspace_id, owner_user_id);
"""


def ensure_crm_saved_views(conn) -> None:
    """Ensure spreadsheet CRM saved-views table exists (SQLite or pg_compat)."""
    conn.executescript(SAVED_VIEWS_DDL)
    conn.commit()
