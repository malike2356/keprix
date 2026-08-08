"""Outreach automation schema SQL (Postgres). Kept in sync with Alembic 024."""

OUTREACH_SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS outreach_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    source_type TEXT,
    daily_cap INTEGER DEFAULT 50,
    timezone TEXT DEFAULT 'Europe/London',
    business_hours_only BOOLEAN DEFAULT true,
    warmup_days INTEGER DEFAULT 3,
    require_approval BOOLEAN DEFAULT false,
    default_sequence_id UUID,
    default_booking_link TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS outreach_sequences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    channel_default TEXT DEFAULT 'email',
    stop_on_reply BOOLEAN DEFAULT true,
    stop_on_booking BOOLEAN DEFAULT true,
    stop_on_unsubscribe BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS outreach_sequence_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_id UUID REFERENCES outreach_sequences(id) ON DELETE CASCADE,
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
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL,
    campaign_id UUID REFERENCES outreach_campaigns(id),
    status TEXT NOT NULL DEFAULT 'new',
    first_name TEXT,
    last_name TEXT,
    email TEXT NOT NULL,
    company TEXT,
    phone TEXT,
    source TEXT DEFAULT 'manual',
    source_url TEXT,
    tags TEXT[],
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS outreach_enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES outreach_leads(id) ON DELETE CASCADE,
    sequence_id UUID REFERENCES outreach_sequences(id),
    current_step INTEGER NOT NULL DEFAULT 0,
    next_run_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS outreach_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enrollment_id UUID REFERENCES outreach_enrollments(id) ON DELETE CASCADE,
    step_id UUID REFERENCES outreach_sequence_steps(id),
    channel TEXT NOT NULL,
    subject TEXT,
    body TEXT NOT NULL,
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    bounced BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS outreach_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES outreach_leads(id),
    message_id UUID REFERENCES outreach_messages(id),
    from_address TEXT NOT NULL,
    subject TEXT,
    body TEXT NOT NULL,
    classification TEXT,
    confidence REAL,
    resolved BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_outreach_campaigns_workspace ON outreach_campaigns(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_sequences_workspace ON outreach_sequences(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_leads_workspace ON outreach_leads(workspace_id);
CREATE INDEX IF NOT EXISTS ix_outreach_leads_email ON outreach_leads(workspace_id, email);
CREATE INDEX IF NOT EXISTS ix_outreach_enrollments_due ON outreach_enrollments(status, next_run_at);
"""
