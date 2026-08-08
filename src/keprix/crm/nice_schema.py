"""Additive SQLite schema for Nice P5 CRM features (452-465)."""

from __future__ import annotations

from typing import Any

NICE_SCHEMA = """
CREATE TABLE IF NOT EXISTS crm_icp_definitions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    pack TEXT NOT NULL DEFAULT 'generic',
    include_rules TEXT NOT NULL DEFAULT '[]',
    exclude_rules TEXT NOT NULL DEFAULT '[]',
    geography TEXT NOT NULL DEFAULT '[]',
    size_band TEXT,
    keywords TEXT NOT NULL DEFAULT '[]',
    sic_codes TEXT NOT NULL DEFAULT '[]',
    notes TEXT,
    active INTEGER NOT NULL DEFAULT 0,
    parent_id TEXT,
    actor_type TEXT,
    actor_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, name, version)
);

CREATE TABLE IF NOT EXISTS crm_teams (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    member_user_ids TEXT NOT NULL DEFAULT '[]',
    round_robin_cursor INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_entity_locks (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    owner_user_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(workspace_id, entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS crm_comments (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    body TEXT NOT NULL,
    mentions TEXT NOT NULL DEFAULT '[]',
    actor_type TEXT,
    actor_id TEXT,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS crm_external_id_map (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    external_id TEXT NOT NULL,
    crm_object_type TEXT NOT NULL,
    crm_object_id TEXT NOT NULL,
    meta_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, provider, external_id, crm_object_type)
);

CREATE TABLE IF NOT EXISTS crm_experiments (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    sequence_id TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    variants_json TEXT NOT NULL DEFAULT '[]',
    traffic_split_json TEXT NOT NULL DEFAULT '{}',
    start_at TEXT,
    end_at TEXT,
    guard_thresholds_json TEXT NOT NULL DEFAULT '{}',
    metrics_json TEXT NOT NULL DEFAULT '{}',
    winner_variant TEXT,
    min_sample INTEGER NOT NULL DEFAULT 50,
    actor_type TEXT,
    actor_id TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_experiment_assignments (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    experiment_id TEXT NOT NULL,
    contact_key TEXT NOT NULL,
    variant TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(workspace_id, experiment_id, contact_key)
);

CREATE TABLE IF NOT EXISTS crm_enrich_provider_runs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed',
    batch_json TEXT NOT NULL DEFAULT '[]',
    patches_json TEXT NOT NULL DEFAULT '[]',
    cost_units REAL NOT NULL DEFAULT 0,
    license_tag TEXT,
    soft_wall_approval_id TEXT,
    actor_type TEXT,
    actor_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_data_quality_jobs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed',
    filters_json TEXT NOT NULL DEFAULT '{}',
    findings_json TEXT NOT NULL DEFAULT '[]',
    soft_wall_approval_id TEXT,
    actor_type TEXT,
    actor_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_template_locales (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    sequence_id TEXT,
    step_order INTEGER NOT NULL DEFAULT 1,
    locale TEXT NOT NULL,
    subject TEXT,
    body TEXT,
    reviewed INTEGER NOT NULL DEFAULT 0,
    compliance_hint TEXT,
    actor_type TEXT,
    actor_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, sequence_id, step_order, locale)
);

CREATE TABLE IF NOT EXISTS crm_channel_templates (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    name TEXT NOT NULL,
    provider_template_id TEXT,
    body TEXT,
    approved INTEGER NOT NULL DEFAULT 0,
    actor_type TEXT,
    actor_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_tracking_events (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    campaign_id TEXT,
    contact_key TEXT,
    event_type TEXT NOT NULL,
    url TEXT,
    raw_url TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_voice_media (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    activity_id TEXT,
    entity_type TEXT,
    entity_id TEXT,
    media_path TEXT,
    transcript TEXT,
    retention_until TEXT,
    consent_recorded INTEGER NOT NULL DEFAULT 0,
    actor_type TEXT,
    actor_id TEXT,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS crm_portal_checklist_acks (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    checklist_version TEXT NOT NULL,
    acknowledged_by TEXT NOT NULL,
    acknowledged_at TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS crm_workspace_nice_settings (
    workspace_id TEXT PRIMARY KEY,
    tracking_enabled INTEGER NOT NULL DEFAULT 0,
    whatsapp_sms_enabled INTEGER NOT NULL DEFAULT 0,
    voice_retention_days INTEGER NOT NULL DEFAULT 30,
    voice_consent_required INTEGER NOT NULL DEFAULT 1,
    default_locale TEXT NOT NULL DEFAULT 'en-GB',
    stale_alert_pct REAL NOT NULL DEFAULT 40.0,
    settings_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_crm_icp_ws ON crm_icp_definitions(workspace_id, active);
CREATE INDEX IF NOT EXISTS ix_crm_ext_map ON crm_external_id_map(workspace_id, provider);
CREATE INDEX IF NOT EXISTS ix_crm_exp_ws ON crm_experiments(workspace_id, status);
CREATE INDEX IF NOT EXISTS ix_crm_track_ws ON crm_tracking_events(workspace_id, event_type);
CREATE INDEX IF NOT EXISTS ix_crm_comments_ent ON crm_comments(workspace_id, entity_type, entity_id);
CREATE INDEX IF NOT EXISTS ix_crm_locks_ent ON crm_entity_locks(workspace_id, entity_type, entity_id);
"""


def ensure_nice_schema(store: Any) -> None:
    """Apply Nice tables and additive entity columns once per store connection."""
    with store._lock:
        store._conn.executescript(NICE_SCHEMA)
        _ensure_party_assignment_columns(store)
        _ensure_deal_attribution_columns(store)
        _ensure_contact_locale_columns(store)
        store._conn.commit()


def _alter_if_missing(store: Any, table: str, column: str, ddl: str) -> None:
    cols = {r[1] for r in store._conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        store._conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def _ensure_party_assignment_columns(store: Any) -> None:
    for table in ("crm_leads", "crm_contacts", "crm_accounts", "crm_deals"):
        _alter_if_missing(store, table, "owner_user_id", "owner_user_id TEXT")
        _alter_if_missing(store, table, "team_id", "team_id TEXT")
        _alter_if_missing(store, table, "sla_due_at", "sla_due_at TEXT")
        _alter_if_missing(store, table, "sla_state", "sla_state TEXT")
        _alter_if_missing(store, table, "icp_id", "icp_id TEXT")
        _alter_if_missing(store, table, "icp_version", "icp_version INTEGER")
        _alter_if_missing(store, table, "preferred_locale", "preferred_locale TEXT")


def _ensure_deal_attribution_columns(store: Any) -> None:
    _alter_if_missing(store, "crm_deals", "attribution_mode", "attribution_mode TEXT")
    _alter_if_missing(store, "crm_deals", "attribution_notes", "attribution_notes TEXT")
    # stripe_customer_id already exists on deals; keep read-only usage.


def _ensure_contact_locale_columns(store: Any) -> None:
    _alter_if_missing(store, "crm_lists", "icp_id", "icp_id TEXT")
    _alter_if_missing(store, "crm_lists", "icp_version", "icp_version INTEGER")
    _alter_if_missing(
        store, "crm_discovery_jobs", "icp_id", "icp_id TEXT"
    )
    _alter_if_missing(
        store, "crm_discovery_jobs", "icp_version", "icp_version INTEGER"
    )
