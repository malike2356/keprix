# Keprix - Prompt 146: LLM Usage Analytics API

## Context

Read `144-llm-usage-analytics-wiring-outline.md`.

Complete Prompt **145** first (persistent `llm_usage_events` must exist).

This prompt ships the **query and aggregation layer** plus REST endpoints consumed
by the web UI and CLI.

Output: `src/keprix/usage/analytics.py`, `src/keprix/usage/routes.py`,
`src/keprix/usage/budget.py`, tests, docs snippet.

## Step 1: Analytics service

`analytics.py`:

```python
class LlmUsageAnalytics:
    async def summary(self, *, days: int = 30, user_id: str | None = None, ...) -> dict
    async def timeseries(self, *, granularity: Literal["day", "hour"], ...) -> list[dict]
    async def breakdown(self, *, dimension: Literal["model", "provider", "channel", "user"], ...) -> list[dict]
    async def list_events(self, *, limit: int, offset: int, ...) -> dict
```

Return shapes:

**summary**

```json
{
  "period_days": 30,
  "request_count": 1240,
  "total_tokens": 4820000,
  "input_tokens": 3200000,
  "output_tokens": 1620000,
  "cache_read_tokens": 450000,
  "total_cost_usd": 12.47,
  "estimated_cost_usd": 11.90,
  "unknown_cost_count": 3,
  "avg_cost_per_request_usd": 0.0101,
  "avg_tokens_per_request": 3887
}
```

**timeseries** (per bucket)

```json
{
  "date": "2026-07-01",
  "request_count": 42,
  "total_tokens": 180000,
  "total_cost_usd": 0.52
}
```

**breakdown** (per dimension value)

```json
{
  "key": "claude-sonnet-4-6",
  "label": "claude-sonnet-4-6",
  "request_count": 320,
  "total_tokens": 2100000,
  "total_cost_usd": 8.12,
  "share_percent": 65.1
}
```

Use SQL aggregation in `LlmUsageStore`; do not load all rows into Python for
summary/timeseries.

## Step 2: Budget store

`budget.py`:

Table `llm_usage_budget` (migration in 145 or new `014b` if 145 already shipped):

- `workspace_id` PK
- `monthly_budget_usd` Numeric nullable
- `alert_threshold_percent` Integer default 80
- `updated_at` timestamptz

Methods:

- `get_budget(workspace_id) -> BudgetConfig`
- `set_budget(workspace_id, monthly_budget_usd, ...)`
- `month_to_date_spend(workspace_id) -> Decimal`
- `budget_status() -> { spent, budget, percent_used, alert: bool }`

## Step 3: API routes

`routes.py` mounted at `/api/usage`:

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/summary` | user | Own or all (admin) summary |
| GET | `/timeseries` | user | Bucketed series |
| GET | `/breakdown/{dimension}` | user | model/provider/channel/user |
| GET | `/events` | admin | Paginated raw events |
| GET | `/export` | admin | CSV stream |
| GET | `/budget` | user | Month-to-date vs budget |
| PUT | `/budget` | admin | Set monthly budget |
| GET | `/pricing/models` | user | Known models + $/1M rates (read-only from usage_pricing) |

Query params (shared): `days`, `from`, `to`, `user_id`, `channel`, `model`,
`provider`, `workspace_id`.

Auth rules:

- Non-admin users: force `user_id` to current user on all endpoints except
  `/pricing/models`
- Admin/owner: optional `user_id` filter; default instance-wide

Register router in `src/keprix/api/server.py`.

## Step 4: Deprecate observability dashboard stub

Update `GET /api/observability/dashboard`:

- Include `usage_summary` from `LlmUsageAnalytics.summary(days=7)` when Prompt 145
  data exists
- Keep `tokens`/`cost` in-memory fields for backward compat but mark deprecated
  in OpenAPI description

## Step 5: CLI commands

Extend `keprix_cli` or add `keprix usage`:

```bash
keprix usage summary [--days 30]
keprix usage breakdown models [--days 30]
keprix usage export --output usage.csv [--days 90]
```

Reuse `InsightsEngine` terminal formatting where helpful, but prefer API/analytics
service as single source of truth.

## Step 6: Insights bridge

File: `src/keprix/agent/insights.py`

Add optional backend mode:

```python
def generate_from_usage_store(self, days=30) -> InsightsReport:
```

When PostgreSQL/SQLite usage store has data, use it instead of SessionDB-only
queries. Keep SessionDB path as fallback for CLI-only installs.

## Step 7: Documentation

Add section to `docs/configuration/environment-variables.md` for usage env vars.

Add `docs/features/llm-usage.md` (short): what is tracked, retention, budget alerts,
difference from SaaS billing (Prompt 78).

## Step 8: Tests

`tests/usage/test_analytics_api.py`:

1. Seed 10 events across 3 models, 2 users, 3 days
2. `GET /api/usage/summary?days=30` totals match seed
3. `GET /api/usage/timeseries?granularity=day` returns 3 buckets
4. `GET /api/usage/breakdown/model` ordering by cost desc
5. Non-admin cannot pass `user_id` for another user (403 or forced filter)
6. `PUT /api/usage/budget` + `GET /api/usage/budget` alert when over threshold
7. CSV export returns header row + event rows

Use TestClient with auth fixtures from `tests/api/`.

## Acceptance Criteria

- All `/api/usage/*` endpoints return real aggregated data from `llm_usage_events`
- Admin and user scoping enforced
- Budget month-to-date uses calendar month UTC
- CSV export works for 1000+ rows without OOM (stream response)
- `pytest tests/usage/test_analytics_api.py` passes
- OpenAPI lists new routes under tag `usage`

## Archive Checklist

Move to `prompts-archive/` and update audit + completed README.
