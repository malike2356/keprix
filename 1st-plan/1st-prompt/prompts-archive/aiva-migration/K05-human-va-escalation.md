# K05: Human VA Escalation on Keprix

**Status: COMPLETED 2026-08-07**

**What was built:**
- Package `keprix/aiva_escalation/` (sqlite store, confidence heuristics, notify log, service, routes, cron seed, bootstrap)
- Alembic `026_aiva_escalation` (`aiva_escalations`, `aiva_human_assist_requests`)
- Tools toolset `escalation`: create/assign/complete/get_queue, `human_assist_request`, `escalation_process_timeouts`
- Carina bridge hook: low confidence or `force_escalate` returns holding message + escalation metadata (`finish_reason=escalated`)
- Dashboard API: `GET /api/aiva/escalations/queue` (+ assign/complete/timeouts)
- Cron: `aiva-escalation-timeout` every 5m
- Tests: `tests/tools/test_aiva_escalation.py` (10 passed)

**Phase:** 2 (Features)
**Priority:** P2
**Depends on:** K01 (agent contract working)
**Target time:** 6 hours
**Location:** Keprix

## What This Builds

Human VA escalation using Keprix's subagent/delegation system. When Aiva's AI reaches a confidence threshold below the configured minimum, it escalates to a human VA. The escalation is invisible to the client, logged, and tracked.

## Why Keprix Subagents are a Natural Fit

- Keprix's `delegate_tool.py` (3,086 lines) already handles task handoff between agents
- Guardrails and input/output validation prevent escalation abuse
- Sandbox execution ensures escalated tasks run in isolation
- Handoff tracking shows exactly what was escalated, when, and to whom

## How It Works

```
User -> Aiva Worker -> Agent loop detects low confidence
                    -> Escalation trigger fires
                    -> Task delegated to Human VA subagent
                    -> Human VA picks up task from queue
                    -> VA completes task
                    -> Result flows back to Aiva Worker
                    -> Aiva presents result to User
```

## Data Model

```sql
CREATE TABLE aiva_escalations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    session_id TEXT,
    escalation_type TEXT NOT NULL,  -- 'low_confidence', 'out_of_scope', 'manual_request', 'safety_flag'
    confidence_score REAL,           -- The AI's confidence when it escalated
    original_input TEXT NOT NULL,    -- What the user asked
    holding_message TEXT,            -- What Aiva told the user while waiting
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, assigned, in_progress, completed, cancelled
    assigned_va TEXT,                -- Which human VA picked it up
    va_response TEXT,                -- The human's response
    channel TEXT,                    -- telegram, email, whatsapp, web
    created_at TIMESTAMPTZ DEFAULT now(),
    assigned_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE TABLE aiva_human_assist_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    urgency TEXT NOT NULL DEFAULT 'normal',  -- normal, urgent
    details TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT now()
);
```

## Keprix Tools

| Tool | Purpose |
|---|---|
| `escalation_create` | Create an escalation when AI confidence is low |
| `escalation_assign` | Assign escalation to a human VA |
| `escalation_complete` | Mark escalation complete with VA response |
| `escalation_get_queue` | Get pending escalations for workspace |
| `human_assist_request` | Manual human assist request from user |

## Escalation Triggers (in Agent Loop)

During `/carina/agent/run`, if the agent's response confidence drops below the workspace threshold:

1. Agent generates a holding message: "Let me check on that for you. One moment."
2. Agent creates escalation record
3. Human VA notified (Telegram, dashboard, or email)
4. VA reviews original input, provides response
5. Response injected back into conversation
6. User sees the answer as if Aiva produced it

## Subagent Configuration

```yaml
# In Keprix config
aiva_escalation:
  confidence_threshold: 0.7  # Escalate when confidence < 0.7
  holding_message_template: "Let me look into that for you. I'll be right back."
  notify_channels:
    - telegram
    - dashboard
  timeout_minutes: 30  # Auto-reassign if no VA picks up within 30 min
```

## Acceptance Criteria

- [x] Agent escalates when confidence < threshold
- [x] Holding message sent to user immediately on escalation
- [x] Human VA receives notification with full context
- [x] VA completes task -> response flows back to user
- [x] Escalation queue visible in dashboard
- [x] Timeout auto-reassigns if no VA picks up
- [x] Full audit trail: who handled what, when
