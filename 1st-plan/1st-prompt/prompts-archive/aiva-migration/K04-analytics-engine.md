# K04: Analytics Engine on Keprix

**Status: COMPLETED 2026-08-07**

**What was built:**
- Package `keprix/aiva_analytics/` (sqlite event + daily store, metrics helpers, OTel export, aggregation service, routes, cron seed, bootstrap)
- Alembic `027_aiva_analytics` (`aiva_analytics_events`, `aiva_analytics_daily`)
- Tools toolset `analytics`: overview/outreach/worker/usage + `analytics_aggregate_daily`
- APIs: `GET /carina/analytics/overview|outreach|worker|usage` (workspace via `X-Workspace-Id`)
- Carina bridge emits agent/tool/worker metrics + `LlmUsageRecorder` channel `aiva` on every `/carina/agent/run`
- Outreach/escalation hooks for emails sent, replies/bookings, escalations
- Cron: `aiva-analytics-daily-aggregate` at `0 8 * * *`
- Tests: `tests/tools/test_aiva_analytics.py` (8 passed)

**Phase:** 2 (Features)
**Priority:** P2
**Depends on:** K01, K02, K03 (data flowing through Keprix)
**Target time:** 8 hours
**Location:** Keprix

## What This Builds

Analytics dashboards for Aiva usage, powered by Keprix's OpenTelemetry stack. Tracks: agent calls, tool usage, token consumption, latency, error rates, outreach metrics, and worker activity.

## Why Keprix is Better for This

- OpenTelemetry is already in Keprix. Carina has no structured observability.
- Agent traces show exactly what happened in every conversation turn.
- Cost metering per workspace for billing.
- Dashboards auto-generated from metrics, not hand-built PHP queries.

## Metrics to Track

### Agent Metrics
- `aiva_agent_calls_total` (counter, labels: workspace_id, worker_id, model)
- `aiva_agent_duration_seconds` (histogram, labels: workspace_id, worker_id)
- `aiva_agent_tokens_total` (counter, labels: workspace_id, worker_id, type)
- `aiva_agent_errors_total` (counter, labels: workspace_id, worker_id, error_type)
- `aiva_tool_calls_total` (counter, labels: workspace_id, tool_name)
- `aiva_tool_duration_seconds` (histogram, labels: workspace_id, tool_name)

### Outreach Metrics
- `aiva_outreach_emails_sent_total` (counter, labels: workspace_id, campaign_id)
- `aiva_outreach_emails_opened_total` (counter, labels: workspace_id, campaign_id)
- `aiva_outreach_emails_clicked_total` (counter, labels: workspace_id, campaign_id)
- `aiva_outreach_replies_total` (counter, labels: workspace_id, classification)
- `aiva_outreach_bookings_total` (counter, labels: workspace_id)
- `aiva_outreach_leads_total` (gauge, labels: workspace_id, status)

### Worker Metrics
- `aiva_worker_active_total` (gauge, labels: workspace_id)
- `aiva_worker_messages_total` (counter, labels: workspace_id, worker_id, channel)
- `aiva_worker_escalations_total` (counter, labels: workspace_id, worker_id)

## Dashboards

### Agent Performance Dashboard
- Calls per hour (line chart)
- P50/P95/P99 latency (line chart)
- Error rate (stat card, red if >1%)
- Token consumption by worker (bar chart)

### Outreach Funnel Dashboard
- Leads by status (funnel chart: new -> contacted -> replied -> booked -> won)
- Response rate (stat card: replies/emails_sent)
- Booking rate (stat card: bookings/replies)
- Win rate (stat card: won/bookings)
- Campaign comparison (table)

### Workspace Usage Dashboard
- Active workers (gauge)
- Messages per channel (pie chart)
- Top tools used (bar chart)
- Monthly token cost (line chart, with cost estimate)

## API Endpoints

| Endpoint | Purpose |
|---|---|
| GET /carina/analytics/overview | Top-level KPIs for workspace |
| GET /carina/analytics/outreach?campaign_id=X | Outreach funnel for a campaign |
| GET /carina/analytics/worker?worker_id=X | Per-worker stats |
| GET /carina/analytics/usage?days=30 | Token/cost usage over time |

## Cron Job

Daily at 08:00: aggregate previous day's metrics into summary table for faster dashboard queries.

## Acceptance Criteria

- [ ] Agent call metrics recorded for every /carina/agent/run call
- [ ] Outreach metrics tracked across the funnel
- [ ] Dashboards load in under 2 seconds
- [ ] Per-workspace isolation: workspace A cannot see workspace B metrics
- [ ] Token/cost estimates within 10% of actual Stripe billing
