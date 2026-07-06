# LLM usage and cost analytics

Keprix records every LLM completion as a row in `llm_usage_events` (PostgreSQL or
SQLite fallback). Use this for operational visibility into API spend on your
self-hosted instance.

## What is tracked

- Input, output, cache, and reasoning tokens
- Estimated USD cost (from `agent/usage_pricing.py`)
- Provider, model, channel (`web_ui`, `api`, `telegram`, `mutation`, etc.)
- Session and user identifiers when available

## API

| Endpoint | Description |
| --- | --- |
| `GET /api/usage/summary` | Totals for a period |
| `GET /api/usage/timeseries` | Daily or hourly buckets |
| `GET /api/usage/breakdown/{dimension}` | By model, provider, channel, or user |
| `GET /api/usage/budget` | Month-to-date spend vs budget |
| `PUT /api/usage/budget` | Set monthly budget (admin) |
| `GET /api/usage/pricing/models` | Known model price catalog |

## Configuration

```bash
KEPRIX_LLM_USAGE_ENABLED=true
KEPRIX_LLM_USAGE_RETENTION_DAYS=90
KEPRIX_LLM_USAGE_SQLITE_FALLBACK=true
```

## CLI

```bash
keprix usage summary --days 30
keprix usage breakdown models --days 30
keprix usage export --output usage.csv --days 90
```

## Product boundary

This is **operational spend visibility** for the instance owner. It is separate
from SaaS billing (Stripe subscriptions in Prompt 78). Langfuse and OpenTelemetry
remain optional external exports; the local dashboard works offline.

## Retention

Rows older than `KEPRIX_LLM_USAGE_RETENTION_DAYS` are pruned on API startup and
via the retention helper in `keprix.usage.retention`.

## Budget alerts

Set `monthly_budget_usd` with `PUT /api/usage/budget`. The status endpoint reports
`percent_used` and `alert` when spend crosses `alert_threshold_percent` (default 80).
