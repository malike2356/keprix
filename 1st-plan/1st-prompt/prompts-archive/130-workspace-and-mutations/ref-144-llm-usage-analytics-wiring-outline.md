# Keprix - Prompt 144: LLM Usage and Cost Analytics Wiring Outline (Reference)

## Purpose

This document is the **reference and dependency map** for adding LLM token usage
and cost monitoring with a dedicated dashboard in the Keprix backend and web UI.

Build through Prompts **145-148** in numeric order. Do not archive this file.

## Dependencies (already archived)

| Prompt | Capability |
| --- | --- |
| 18 | API surface, health, request log |
| 57 | Agent traces, in-memory token/cost meters, `/api/observability/*` |
| 103 | UI foundation, theme, ApexCharts-ready admin shell |
| 118 | Admin overview dashboard, stat cards, charts |
| 136 | Workspace shell, SWR data fetching patterns |
| 78 | SaaS billing (separate concern; do not conflate with LLM ops metrics) |

## Current State (what exists today)

### Recording (fragmented)

| Source | What it stores | Persistence |
| --- | --- | --- |
| `conversation_loop.py` | Per-call tokens + cost via `SessionDB.update_token_counts` | SQLite session DB |
| `agent/insights.py` | Aggregates session rows for `/insights` CLI | Read-only over SQLite |
| `agent/usage_pricing.py` | `estimate_usage_cost`, model pricing tables | In-memory + provider APIs |
| `observability/metrics.py` | `MetricsStore` with `metric_type=provider_request` | PostgreSQL, 90-day |
| `public_api/usage.py` | API key token totals | PostgreSQL metrics |
| `backend/observability/token_meter.py` | Per-run token dicts | **In-memory only** |
| `backend/observability/cost_meter.py` | Per-run USD | **In-memory only** |
| `api/chat_inference.py` | Web chat streaming | **No usage recorded** |
| Langfuse plugin | External observability | Optional plugin |

### API (partial)

- `GET /api/observability/dashboard` returns in-memory meters (lost on restart)
- No timeseries, model breakdown, or user/channel filters for LLM spend
- No workspace-facing usage page

### UI (missing)

- Admin dashboard shows conversations/tools/memory, **not** LLM cost
- `/evals` covers quality benchmarks, not operational token spend
- Desktop app has `/usage` slash for session-only view; web has no equivalent

## Target Architecture

```
Every LLM completion (chat, agent loop, public API, eval judge, synthesis)
  -> LlmUsageRecorder.record(LlmUsageEvent)
  -> PostgreSQL llm_usage_events (or SQLite fallback)
  -> LlmUsageAnalyticsService (rollups)
  -> GET /api/usage/*
  -> /usage workspace dashboard + /dashboard/usage admin analytics
```

## Event Schema (canonical)

```python
@dataclass
class LlmUsageEvent:
    id: str
    recorded_at: datetime
    workspace_id: str
    user_id: str | None
    session_id: str | None
    run_id: str | None
    channel: str          # web_ui, telegram, api, eval, mutation, cron, ...
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    reasoning_tokens: int
    total_tokens: int
    cost_usd: Decimal | None
    cost_status: str      # actual, estimated, included, unknown
    cost_source: str
    duration_ms: int | None
    metadata: dict        # endpoint, api_key_id, persona, etc.
```

## Phase Map

| Phase | Prompt | Outcome |
| --- | --- | --- |
| 1 | 145 | Persistent store, recorder, instrumentation at all LLM call sites |
| 2 | 146 | Analytics API: summary, timeseries, breakdowns, export |
| 3 | 147 | Workspace `/usage` dashboard (charts, filters, session drill-down) |
| 4 | 148 | Admin usage analytics, nav, budgets/alerts, overview stat cards |

## Instrumentation Points (Prompt 145)

Wire `LlmUsageRecorder` at minimum:

1. `agent/conversation_loop.py` (after each LLM response with `canonical_usage`)
2. `api/chat_inference.py` (capture usage from final stream chunk or non-stream response)
3. `public_api/` chat completions and embeddings handlers
4. `agent/plugin_llm.py` plugin path
5. `agent/keprix/synthesiser.py` mutation synthesis calls
6. `backend/evals/graders.py` LLM judge calls (tag `channel=eval`)
7. Bridge existing `record_tokens` / `record_cost` in `agent_trace.py` to persist
   events instead of only in-memory meters

Optional backfill: one-time import from `SessionDB` session token aggregates into
`llm_usage_events` with `channel=backfill` (best-effort, not required for AC).

## Analytics API Shape (Prompt 146)

| Endpoint | Purpose |
| --- | --- |
| `GET /api/usage/summary` | Totals for period (tokens, cost, request count) |
| `GET /api/usage/timeseries` | Daily/hourly buckets |
| `GET /api/usage/breakdown/models` | By model |
| `GET /api/usage/breakdown/providers` | By provider |
| `GET /api/usage/breakdown/channels` | By channel |
| `GET /api/usage/breakdown/users` | Admin only |
| `GET /api/usage/events` | Paginated raw events (admin) |
| `GET /api/usage/export` | CSV export (admin) |
| `GET /api/usage/budget` | Current month vs budget |
| `PUT /api/usage/budget` | Set monthly budget USD (admin) |

Query params: `days`, `from`, `to`, `user_id`, `channel`, `model`, `provider`.

Auth: workspace users see own usage; admin/owner sees instance totals.

## Workspace UI (Prompt 147)

Route: `/usage` in `(workspace)` group.

Sections:

- Period selector (7d / 30d / 90d / custom)
- Stat cards: total tokens, estimated cost, API calls, avg cost per call
- Line chart: daily tokens + cost (dual axis or toggle)
- Donut/bar: spend by model
- Table: recent calls (time, model, tokens, cost, channel, session link)
- Link to `/chat/{sessionId}` when session_id present

## Admin UI (Prompt 148)

Route: `/dashboard/usage` in `(admin)` group.

Adds to admin overview:

- Stat card: "LLM spend (30d)" on `/dashboard`
- Full page: all workspace UI charts plus user breakdown, channel breakdown,
  budget progress bar, alert banner when over threshold
- Sidebar nav item under Agent or Operations

## Configuration

```bash
KEPRIX_LLM_USAGE_ENABLED=true
KEPRIX_LLM_USAGE_RETENTION_DAYS=90
KEPRIX_LLM_USAGE_MONTHLY_BUDGET_USD=   # optional; empty = no budget alerts
KEPRIX_LLM_USAGE_SQLITE_FALLBACK=true  # when PostgreSQL unavailable
```

## Product Boundaries

- **LLM usage analytics** = operational visibility for the self-hosted instance owner
  (API spend, model mix, channel cost).
- **Prompt 78 billing** = customer subscriptions and Stripe; do not bill end users
  from usage events in these prompts.
- **Langfuse / OTEL** = optional external export; local dashboard must work offline.

## Files Checklist

**Backend**

- `src/keprix/usage/` (new package) or `src/keprix/observability/llm_usage/`
- `migrations/versions/014_llm_usage_events.py`
- `src/keprix/api/chat_inference.py`
- `src/keprix/agent/conversation_loop.py`
- `src/keprix/backend/observability/routes.py` (deprecate or proxy to new API)
- `src/keprix/ui_contract/navigation.py`

**Frontend**

- `frontend/src/app/(workspace)/usage/page.tsx`
- `frontend/src/lib/usage-api.ts`
- `frontend/src/components/usage/*`
- `frontend/src/app/(admin)/dashboard/usage/page.tsx`
- `frontend/src/lib/navigation.ts`
- `frontend/src/lib/admin-dashboard-api.ts` (extend stats)

**Tests**

- `tests/usage/test_recorder.py`
- `tests/usage/test_analytics_api.py`
- `tests/frontend/test_usage_dashboard.py`

## Honest Scope Note

Prompts 145-147 deliver full instance-owner visibility for web chat and agent
paths. Prompt 148 adds admin operations polish. Historical data before ship date
requires backfill or starts fresh from deploy.
