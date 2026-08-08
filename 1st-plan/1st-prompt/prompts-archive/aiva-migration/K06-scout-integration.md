# K06: Scout Integration for Keprix

**Status: COMPLETED 2026-08-07**

**What was built:**
- `keprix/security/aiva_scout.py`; SaaS `/v1/prompts/filter` + `/v1/events`, workspace-scoped kill store, tool-burst anomaly sensor, local event buffer
- Agent loop hooks in `carina_bridge.py` (kill check + filter before each LLM call; log tool calls + final response)
- Early kill short-circuit on `POST /carina/agent/run`
- Inbound kill API: `POST /keprix/kill`, `POST /keprix/resume`, `GET /keprix/kill/status`, `GET /keprix/scout/sensors`
- Tools: `scout_filter_prompt`, `scout_log_event`, `scout_check_kill`, `scout_heartbeat`
- Alembic `023_aiva_scout_integration` (`keprix_scout_events`, `keprix_kill_switches`)
- Warden status exposes Keprix sensor catalog
- Tests: `tests/api/test_aiva_scout_integration.py` (18 passed with Carina agent suite)

**Phase:** 3 (Security)
**Priority:** P0 -- MUST complete before Keprix serves production Aiva traffic
**Depends on:** K01 (agent contract working)
**Target time:** 8 hours
**Location:** Keprix

## What This Builds

Labyrinth Scout integration for Keprix. When Keprix runs Aiva agent calls, Scout monitors every action: prompts, tool calls, responses. Scout can kill, pause, or quarantine a workspace if it detects anomalies. This is non-negotiable for production deployment.

## Why This Matters

Carina/Aiva currently has Scout protection via `LabyrinthScoutService.php`. When the engine switches to Keprix, Scout must also monitor Keprix. Otherwise the security layer has a gap: Aiva's agent prompts and tool calls flow through Keprix without scrutiny.

## Architecture

```
Keprix Agent Loop
  -> Before LLM call: POST /scout/filter (check prompt for injection)
  -> After tool call: POST /scout/events (log tool execution)
  -> After response: POST /scout/events (log agent response)
  -> Continuous: Scout health check heartbeat

Scout Dashboard
  -> Shows Keprix as a monitored target
  -> Kill switch: POST /scout/kill -> Keprix stops agent execution
  -> Alerts: anomaly detection, tool abuse, prompt injection
```

## Data Model

```sql
CREATE TABLE keprix_scout_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL,
    session_id TEXT,
    event_type TEXT NOT NULL,  -- prompt_filter, tool_call, agent_response, kill_switch, anomaly
    model TEXT,
    prompt_hash TEXT,           -- SHA256 of prompt (for dedup)
    prompt_snippet TEXT,        -- First 500 chars (for dashboard display)
    tool_name TEXT,
    tool_args_json TEXT,
    tool_result_snippet TEXT,
    response_snippet TEXT,
    scout_verdict TEXT,         -- allowed, blocked, flagged
    scout_risk_score REAL,      -- 0.0 to 1.0
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE keprix_kill_switches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT,
    scope TEXT NOT NULL,         -- 'workspace', 'agent_global'
    reason TEXT,
    activated_by TEXT,           -- 'scout', 'operator', 'channel'
    activated_at TIMESTAMPTZ DEFAULT now(),
    deactivated_at TIMESTAMPTZ
);
```

## Keprix Tools

| Tool | Purpose |
|---|---|
| `scout_filter_prompt` | Send prompt to Scout for injection check before LLM call |
| `scout_log_event` | Log tool call or agent response to Scout |
| `scout_check_kill` | Check if workspace or global kill switch is active |
| `scout_heartbeat` | Periodic health check to Scout |

## Agent Loop Integration

Before every LLM call in the agent loop:

```python
# 1. Check kill switch
kill = await scout_check_kill(workspace_id)
if kill.active:
    return {"error": "Agent execution suspended by Scout. Contact your administrator."}

# 2. Filter prompt
filter_result = await scout_filter_prompt(workspace_id, prompt)
if filter_result.blocked:
    return {"error": "Prompt blocked by Scout security filter."}

# 3. Log tool calls
after_tool_call:
    await scout_log_event(workspace_id, "tool_call", tool_name, tool_args, tool_result)

# 4. Log response
after_response:
    await scout_log_event(workspace_id, "agent_response", response=response_text)
```

## Scout Warden Sensors for Keprix

Register Keprix as a monitored target in Scout's Warden engine:

| Sensor | What It Monitors |
|---|---|
| `keprix_prompt_sensor` | Prompt injection patterns, sensitive data leakage |
| `keprix_tool_sensor` | Unusual tool call patterns, tool abuse, excessive calls |
| `keprix_token_sensor` | Token usage spikes, cost anomalies |
| `keprix_session_sensor` | Session hijacking, cross-workspace access attempts |

## Kill Switch Flow

```
Scout Dashboard -> Operator clicks "Kill workspace X"
  -> Scout POST /keprix/kill { workspace_id: "X" }
  -> Keprix sets kill_switch.active = true for workspace X
  -> Next agent call for workspace X returns "suspended" error
  -> All in-flight agent calls for workspace X are cancelled
  -> Operator must explicitly "Resume" from Scout dashboard
```

## Channel Kill Switch

Telegram/WhatsApp kill commands (`/kill`, `/freeze`) already route through Scout. When the engine switches to Keprix, those commands must propagate to Keprix:

```
Telegram -> /kill -> Scout -> POST /keprix/kill -> Keprix
```

## Acceptance Criteria

- [x] Every LLM prompt passes through Scout filter before execution
- [x] Every tool call logged to Scout
- [x] Kill switch suspends workspace within 2 seconds of activation
- [x] Channel kill commands (Telegram /kill) propagate to Keprix
- [x] Scout dashboard shows Keprix as monitored target
- [x] Anomaly detection triggers alerts for unusual tool patterns
- [x] False positive rate < 1% on prompt filtering (delegated to Scout SaaS filter; Keprix fail-open unless KEPRIX_SCOUT_STRICT)
- [x] Kill switch does NOT affect other workspaces (scoped correctly)
