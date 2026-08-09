"""Postgres TEXT-id outreach schema (parity with SQLite store + ops).

Supersedes the unused UUID tables from Alembic 024 / outreach/schema.py.
Every outreach table includes workspace_id TEXT NOT NULL.
"""

from __future__ import annotations

OUTREACH_PG_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS outreach_campaigns (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    source_type TEXT,
    daily_cap INTEGER DEFAULT 50,
    timezone TEXT DEFAULT 'Europe/London',
    business_hours_only INTEGER DEFAULT 1,
    warmup_days INTEGER DEFAULT 3,
    require_approval INTEGER DEFAULT 0,
    default_sequence_id TEXT,
    default_booking_link TEXT,
    email_account_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_sequences (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    channel_default TEXT DEFAULT 'email',
    stop_on_reply INTEGER DEFAULT 1,
    stop_on_booking INTEGER DEFAULT 1,
    stop_on_unsubscribe INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_sequence_steps (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    sequence_id TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    channel TEXT NOT NULL DEFAULT 'email',
    subject TEXT,
    body TEXT NOT NULL,
    cta TEXT,
    link TEXT,
    delay_hours INTEGER NOT NULL DEFAULT 24,
    UNIQUE(sequence_id, step_order)
);

CREATE TABLE IF NOT EXISTS outreach_leads (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    campaign_id TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    first_name TEXT,
    last_name TEXT,
    email TEXT NOT NULL,
    company TEXT,
    phone TEXT,
    source TEXT DEFAULT 'manual',
    source_url TEXT,
    tags TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_enrollments (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    lead_id TEXT NOT NULL,
    sequence_id TEXT NOT NULL,
    current_step INTEGER NOT NULL DEFAULT 0,
    next_run_at TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    locked_until TEXT,
    locked_by TEXT,
    attempt_count INTEGER DEFAULT 0,
    last_error TEXT,
    last_claimed_at TEXT,
    dead_letter_at TEXT,
    correlation_id TEXT
);

CREATE TABLE IF NOT EXISTS outreach_messages (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    enrollment_id TEXT NOT NULL,
    step_id TEXT,
    step_order INTEGER,
    channel TEXT NOT NULL,
    subject TEXT,
    body TEXT NOT NULL,
    sent_at TEXT,
    delivered_at TEXT,
    opened_at TEXT,
    clicked_at TEXT,
    bounced INTEGER DEFAULT 0,
    approval_status TEXT DEFAULT 'none',
    approval_id TEXT,
    idempotency_key TEXT,
    provider TEXT,
    provider_message_id TEXT,
    provider_thread_id TEXT,
    mailbox TEXT,
    delivery_state TEXT DEFAULT 'draft',
    last_provider_event_at TEXT,
    send_error TEXT,
    correlation_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_provider_events (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    event_type TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    provider_message_id TEXT,
    message_id TEXT,
    payload_json TEXT,
    received_at TEXT NOT NULL,
    applied_at TEXT,
    signature_ok INTEGER DEFAULT 1,
    UNIQUE(workspace_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS outreach_replies (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    lead_id TEXT,
    message_id TEXT,
    from_address TEXT NOT NULL,
    subject TEXT,
    body TEXT NOT NULL,
    classification TEXT,
    confidence REAL,
    resolved INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_control (
    workspace_id TEXT PRIMARY KEY,
    paused INTEGER NOT NULL DEFAULT 0,
    reason TEXT,
    updated_by TEXT,
    updated_at TEXT NOT NULL,
    default_email_account_id TEXT,
    settings_json TEXT
);

CREATE TABLE IF NOT EXISTS outreach_lists (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    tags TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_list_members (
    workspace_id TEXT NOT NULL,
    list_id TEXT NOT NULL,
    lead_id TEXT NOT NULL,
    PRIMARY KEY (list_id, lead_id)
);

CREATE TABLE IF NOT EXISTS outreach_bookings (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    lead_id TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT,
    status TEXT NOT NULL DEFAULT 'scheduled',
    notes TEXT,
    attendee_name TEXT,
    attendee_email TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_approvals (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    message_id TEXT,
    enrollment_id TEXT,
    lead_id TEXT,
    recipient TEXT NOT NULL,
    subject TEXT,
    draft_body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    campaign_id TEXT,
    created_at TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS outreach_scheduler_heartbeats (
    workspace_id TEXT NOT NULL DEFAULT '',
    worker_id TEXT NOT NULL,
    last_beat_at TEXT NOT NULL,
    queue_depth INTEGER DEFAULT 0,
    metadata_json TEXT,
    PRIMARY KEY (workspace_id, worker_id)
);

CREATE INDEX IF NOT EXISTS ix_outreach_campaigns_workspace ON outreach_campaigns(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_sequences_workspace ON outreach_sequences(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_steps_workspace ON outreach_sequence_steps(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_leads_workspace ON outreach_leads(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_leads_email ON outreach_leads(workspace_id, email);
CREATE INDEX IF NOT EXISTS ix_outreach_enrollments_ws ON outreach_enrollments(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_enrollments_due ON outreach_enrollments(workspace_id, status, next_run_at);
CREATE INDEX IF NOT EXISTS ix_outreach_enrollments_lease ON outreach_enrollments(status, locked_until);
CREATE INDEX IF NOT EXISTS ix_outreach_messages_ws ON outreach_messages(workspace_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_outreach_messages_idem ON outreach_messages(workspace_id, idempotency_key);
CREATE INDEX IF NOT EXISTS ix_outreach_messages_provider_mid ON outreach_messages(workspace_id, provider_message_id);
CREATE INDEX IF NOT EXISTS ix_outreach_provider_events_ws ON outreach_provider_events(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_replies_ws ON outreach_replies(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_lists_ws ON outreach_lists(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_list_members_ws ON outreach_list_members(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_bookings_ws ON outreach_bookings(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_approvals_ws ON outreach_approvals(workspace_id, status);
CREATE INDEX IF NOT EXISTS ix_outreach_scheduler_hb_ws ON outreach_scheduler_heartbeats(workspace_id);
"""

OUTREACH_DROP_UUID_TABLES_SQL = """
DROP TABLE IF EXISTS outreach_replies CASCADE;
DROP TABLE IF EXISTS outreach_messages CASCADE;
DROP TABLE IF EXISTS outreach_enrollments CASCADE;
DROP TABLE IF EXISTS outreach_sequence_steps CASCADE;
DROP TABLE IF EXISTS outreach_leads CASCADE;
DROP TABLE IF EXISTS outreach_sequences CASCADE;
DROP TABLE IF EXISTS outreach_campaigns CASCADE;
DROP TABLE IF EXISTS outreach_approvals CASCADE;
DROP TABLE IF EXISTS outreach_bookings CASCADE;
DROP TABLE IF EXISTS outreach_list_members CASCADE;
DROP TABLE IF EXISTS outreach_lists CASCADE;
DROP TABLE IF EXISTS outreach_control CASCADE;
"""

OUTREACH_TABLE_NAMES: tuple[str, ...] = (
    "outreach_campaigns",
    "outreach_sequences",
    "outreach_sequence_steps",
    "outreach_leads",
    "outreach_enrollments",
    "outreach_messages",
    "outreach_provider_events",
    "outreach_replies",
    "outreach_control",
    "outreach_lists",
    "outreach_list_members",
    "outreach_bookings",
    "outreach_approvals",
    "outreach_scheduler_heartbeats",
)


def _outreach_needs_text_rebuild(conn) -> bool:
    """True when legacy UUID 024 tables (or missing workspace_id) are present."""
    try:
        row = conn.execute(
            """
            SELECT data_type FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'outreach_campaigns'
              AND column_name = 'id'
            """
        ).fetchone()
    except Exception:
        row = None
    if row is not None:
        dtype = str(row[0]).lower()
        if "uuid" in dtype:
            return True
    for table in (
        "outreach_sequence_steps",
        "outreach_enrollments",
        "outreach_messages",
        "outreach_replies",
    ):
        try:
            cols = {str(r[1]) for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        except Exception:
            cols = set()
        if cols and "workspace_id" not in cols:
            return True
    return False


def ensure_outreach_pg_schema(conn) -> None:
    """Apply TEXT-id outreach DDL; replace unused UUID 024 tables when detected."""
    if _outreach_needs_text_rebuild(conn):
        conn.executescript(OUTREACH_DROP_UUID_TABLES_SQL)
    # Apply DDL statement-by-statement so one failed index on an older table
    # does not block additive ensure_scheduler_columns.
    for stmt in OUTREACH_PG_SCHEMA_SQL.split(";"):
        chunk = stmt.strip()
        if not chunk:
            continue
        # Lease index requires additive columns on upgraded DBs; skip here.
        if "ix_outreach_enrollments_lease" in chunk:
            continue
        try:
            conn.execute(chunk)
        except Exception:
            pass
    try:
        conn.commit()
    except Exception:
        pass
    from keprix.outreach.store import ensure_delivery_columns, ensure_scheduler_columns

    ensure_scheduler_columns(conn)
    ensure_delivery_columns(conn)
