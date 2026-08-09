"""Postgres DDL for CRM tables (TEXT ids, parity with crm/schema.py)."""

from __future__ import annotations

from keprix.crm.schema import (
    INGESTION_JOBS_DDL,
    LEAD_INGESTION_COLUMNS,
    SQLITE_SCHEMA,
    ensure_crm_saved_views,
)

# SQLite schema already uses TEXT primary keys and portable types.
CRM_PG_SCHEMA_SQL = SQLITE_SCHEMA

CRM_TABLE_NAMES: tuple[str, ...] = (
    "crm_accounts",
    "crm_leads",
    "crm_ingestion_jobs",
    "crm_contacts",
    "crm_deals",
    "crm_activities",
    "crm_lists",
    "crm_list_memberships",
    "crm_enrichment_jobs",
    "crm_consent_records",
    "crm_suppression_entries",
    "crm_field_provenance",
    "crm_source_records",
    "crm_merge_suggestions",
    "crm_merge_history",
    "crm_discovery_jobs",
    "crm_outbox",
    "crm_idempotency",
    "crm_contactability_decisions",
    "crm_sender_readiness",
    "crm_kill_switches",
    "crm_saved_views",
    "crm_funnel_runs",
    "crm_funnel_run_steps",
)


def ensure_crm_pg_schema(conn) -> None:
    """Apply CREATE TABLE IF NOT EXISTS + additive lead columns on a pg_compat conn."""
    conn.executescript(CRM_PG_SCHEMA_SQL)
    conn.executescript(INGESTION_JOBS_DDL)
    existing = {row[1] for row in conn.execute("PRAGMA table_info(crm_leads)").fetchall()}
    for name, ddl in LEAD_INGESTION_COLUMNS:
        if name not in existing:
            alter_ddl = ddl
            if name == "custom_fields" and "NOT NULL" in ddl:
                alter_ddl = "custom_fields TEXT DEFAULT '{}'"
            conn.execute(f"ALTER TABLE crm_leads ADD COLUMN {alter_ddl}")
    ensure_crm_saved_views(conn)
    try:
        from keprix.crm.funnel_orchestrator import ensure_funnel_run_tables

        ensure_funnel_run_tables(conn)
    except Exception:
        pass
    conn.commit()
