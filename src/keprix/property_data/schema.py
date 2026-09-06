"""Idempotent schema for the owned property datasets."""

from __future__ import annotations

SCHEMA = """
CREATE TABLE IF NOT EXISTS property_base (uprn TEXT PRIMARY KEY, address_full TEXT NOT NULL, postcode TEXT NOT NULL DEFAULT '', address_hash TEXT NOT NULL DEFAULT '', first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS property_sold_prices (id TEXT PRIMARY KEY, uprn TEXT NOT NULL DEFAULT '', price_gbp INTEGER NOT NULL, sale_date TEXT NOT NULL, property_type TEXT NOT NULL DEFAULT '', tenure TEXT NOT NULL DEFAULT '', new_build INTEGER NOT NULL DEFAULT 0, source TEXT NOT NULL DEFAULT 'land_registry_ppd', ingested_at TEXT NOT NULL, transaction_id TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS property_epc (id TEXT PRIMARY KEY, uprn TEXT NOT NULL DEFAULT '', current_energy_rating TEXT NOT NULL DEFAULT '', potential_energy_rating TEXT NOT NULL DEFAULT '', current_energy_efficiency INTEGER, inspection_date TEXT NOT NULL DEFAULT '', floor_area_m2 REAL, source TEXT NOT NULL DEFAULT 'epc_open_data', ingested_at TEXT NOT NULL, certificate_id TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS property_company_ownership (id TEXT PRIMARY KEY, uprn TEXT NOT NULL DEFAULT '', company_number TEXT NOT NULL DEFAULT '', country_of_incorporation TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT 'ccod_ocod', ingested_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS property_signals (id TEXT PRIMARY KEY, uprn TEXT NOT NULL, signal_type TEXT NOT NULL, value TEXT NOT NULL DEFAULT '', strength REAL NOT NULL DEFAULT 0, computed_at TEXT NOT NULL, UNIQUE(uprn, signal_type));
CREATE TABLE IF NOT EXISTS property_ingest_state (source TEXT PRIMARY KEY, last_ingest_at TEXT NOT NULL DEFAULT '', last_status TEXT NOT NULL DEFAULT 'never', row_count INTEGER NOT NULL DEFAULT 0, error TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS provider_api_usage (id TEXT PRIMARY KEY, provider TEXT NOT NULL, endpoint TEXT NOT NULL DEFAULT '', calls INTEGER NOT NULL DEFAULT 0, last_called_at TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS property_api_calls (id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, key_id TEXT NOT NULL DEFAULT '', endpoint TEXT NOT NULL, uprn TEXT NOT NULL DEFAULT '', postcode TEXT NOT NULL DEFAULT '', cost_tokens REAL NOT NULL DEFAULT 0, called_at TEXT NOT NULL, idempotency_key TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS property_discovery_configs (workspace_id TEXT PRIMARY KEY, enabled_signals TEXT NOT NULL DEFAULT 'below_market,high_turnover,long_hold,overseas_owner', min_score REAL NOT NULL DEFAULT 0.5, max_results INTEGER NOT NULL DEFAULT 50, region_filter TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS property_saved_searches (id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, name TEXT NOT NULL DEFAULT '', criteria_json TEXT NOT NULL DEFAULT '{}', run_schedule TEXT NOT NULL DEFAULT 'weekly', active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, last_run_at TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS property_saved_search_matches (id TEXT PRIMARY KEY, saved_search_id TEXT NOT NULL, uprn TEXT NOT NULL, score REAL NOT NULL DEFAULT 0, signals_json TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL DEFAULT 'new', found_at TEXT NOT NULL, UNIQUE(saved_search_id,uprn));
CREATE TABLE IF NOT EXISTS property_deal_handoffs (id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, match_id TEXT NOT NULL UNIQUE, deal_id TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS property_calculator_settings (workspace_id TEXT PRIMARY KEY, overrides_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL DEFAULT '');
"""


def ensure_schema(connection) -> None:
    connection.executescript(SCHEMA)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(property_api_calls)").fetchall()}
    if "idempotency_key" not in columns:
        connection.execute("ALTER TABLE property_api_calls ADD COLUMN idempotency_key TEXT NOT NULL DEFAULT ''")
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_property_api_calls_idempotency "
        "ON property_api_calls(workspace_id, idempotency_key) WHERE idempotency_key <> ''"
    )
    connection.commit()
