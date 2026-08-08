# K02: Outreach Automation Engine on Keprix

**Status: COMPLETED 2026-08-07**

**What was built:**
- Package `keprix/outreach/` (sqlite store mirroring Postgres schema, service, classify, bootstrap, cron_seed)
- Alembic `024_outreach_automation` (campaigns, sequences, steps, leads, enrollments, messages, replies)
- Tools toolset `outreach`: create campaign/sequence, add leads (CSV), enroll, process_due, classify_reply, move_lead, pipeline, campaign stats, daily digest, scan_replies
- Cron seeds: `outreach-process-due` (every 5m), `outreach-scan-replies` (every 2m), `outreach-daily-digest` (08:00)
- API lifespan: ensure tables + seed cron jobs
- Tests: `tests/tools/test_outreach_automation.py` (7 passed)

**Phase:** 2 (Features)
**Priority:** P1
**Depends on:** K01 (agent contract working)
**Target time:** 12 hours
**Location:** Keprix

## What This Builds

Outreach automation running natively on Keprix. Sequences, campaigns, lead tracking, and pipeline management powered by Keprix cron + agent loop. This replaces the PHP outreach code with a Keprix-native implementation that Carina calls via the agent contract.

## Why Keprix is Better for This

- Keprix cron handles sequence scheduling natively (no need for Laravel scheduler)
- Agent loop can make decisions mid-sequence (e.g., classify a reply, decide next step)
- Memory system persists lead state across sessions
- pgvector enables semantic lead search and deduplication

## Data Model

### Tables (Keprix PostgreSQL)

```sql
CREATE TABLE outreach_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',  -- draft, active, paused, completed
    source_type TEXT,                       -- manual, csv_import, youtube_comment, email
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

CREATE TABLE outreach_sequences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    channel_default TEXT DEFAULT 'email',
    stop_on_reply BOOLEAN DEFAULT true,
    stop_on_booking BOOLEAN DEFAULT true,
    stop_on_unsubscribe BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE outreach_sequence_steps (
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

CREATE TABLE outreach_leads (
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

CREATE TABLE outreach_enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES outreach_leads(id) ON DELETE CASCADE,
    sequence_id UUID REFERENCES outreach_sequences(id),
    current_step INTEGER NOT NULL DEFAULT 0,
    next_run_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'active',  -- active, completed, stopped_reply, stopped_booking, stopped_unsubscribe
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE outreach_messages (
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

CREATE TABLE outreach_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES outreach_leads(id),
    message_id UUID REFERENCES outreach_messages(id),
    from_address TEXT NOT NULL,
    subject TEXT,
    body TEXT NOT NULL,
    classification TEXT,  -- interested, booking_intent, question, objection, not_interested, not_now, unsubscribe, ooo
    confidence REAL,
    resolved BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

## Keprix Tools

| Tool | Purpose |
|---|---|
| `outreach_create_campaign` | Create a new outreach campaign |
| `outreach_create_sequence` | Create a multi-step sequence |
| `outreach_add_leads` | Add leads (single or bulk CSV) |
| `outreach_enroll_lead` | Enroll a lead in a sequence |
| `outreach_process_due` | Process all due sequence steps (called by cron) |
| `outreach_classify_reply` | Classify an inbound reply using LLM |
| `outreach_move_lead` | Move lead between pipeline stages |
| `outreach_get_pipeline` | Get pipeline board with counts |
| `outreach_get_campaign_stats` | Stats for a campaign |

## Cron Jobs

| Cron | Schedule | Purpose |
|---|---|---|
| `outreach-process-due` | Every 5 minutes | Process all due sequence steps. Send pending messages. |
| `outreach-scan-replies` | Every 2 minutes | Scan email inbox for replies. Classify. Update pipeline. |
| `outreach-daily-digest` | Daily 08:00 | Send workspace owner a summary: new leads, replies, bookings |

## Agent Loop Integration

When the agent processes a lead reply:

1. Cron detects inbound reply
2. Agent classifies reply (LLM call)
3. If booking_intent: agent triggers calendar booking flow
4. If objection: agent drafts a response addressing the objection
5. If unsubscribe: agent stops sequence
6. Agent updates pipeline stage
7. Agent notifies workspace owner (Telegram/webhook)

## Acceptance Criteria

- [x] Campaign CRUD works via Keprix tools
- [x] Sequences with 3+ steps execute on schedule
- [x] Leads flow through pipeline stages
- [x] Reply classification correctly identifies booking_intent, objection, unsubscribe
- [x] Cron processes due steps without manual trigger
- [x] Daily digest sent to workspace owner
