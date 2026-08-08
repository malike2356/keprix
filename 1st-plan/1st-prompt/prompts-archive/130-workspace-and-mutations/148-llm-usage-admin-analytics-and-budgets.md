# Keprix - Prompt 148: Admin LLM Usage Analytics and Budget Alerts

## Context

Read `144-llm-usage-analytics-wiring-outline.md`.

Complete Prompts **145-147** first.

This prompt adds **instance-wide admin analytics**: owner dashboard integration,
user/channel breakdowns, budget configuration UI, CSV export, and alert surfacing
on the admin overview page.

Output: `frontend/src/app/(admin)/dashboard/usage/`,
admin components, backend notification hook, tests.

Depends on Prompt **118** (admin dashboard shell, StatCard, ApexCharts).

## Step 1: Admin API extensions

Ensure Prompt 146 endpoints support admin views (verify, extend if missing):

- `GET /api/usage/breakdown/user` with per-user totals
- `GET /api/usage/events?limit=50&offset=0` for admin event log
- `GET /api/usage/export?days=90` CSV download

Add admin-only aggregate for overview card:

`GET /api/usage/summary?days=30` (no user filter) used by dashboard stat.

## Step 2: Overview stat card

File: `frontend/src/app/(admin)/dashboard/page.tsx`

Add fifth stat card (or replace least critical card on lg breakpoint):

```typescript
<StatCard
  title="LLM spend (30d)"
  value={formatUsd(stats?.llmSpend30d ?? 0)}
  loading={statsLoading}
  icon={<IconCurrencyDollar size={22} />}
  color="warning"
  href="/dashboard/usage"
/>
```

Extend `fetchDashboardStats` in `frontend/src/lib/admin-dashboard-api.ts` and
`src/keprix/api/stats_routes.py` (or admin routes) to include `llmSpend30d`,
`llmTokens30d`, `llmRequestCount30d` from `LlmUsageAnalytics.summary(days=30)`.

## Step 3: Admin usage page

`frontend/src/app/(admin)/dashboard/usage/page.tsx`

Sections beyond workspace `/usage` page:

1. **Budget panel** (top)
   - Editable monthly budget USD (admin only)
   - Progress bar: spent / budget
   - Alert threshold slider (default 80%)
   - Save via `PUT /api/usage/budget`

2. **Instance summary** (same stat cards as workspace, instance-wide)

3. **Charts row**
   - Daily cost timeseries (30d)
   - Stacked or grouped bar: cost by channel (web_ui, telegram, api, eval, ...)

4. **User breakdown table**
   - User, requests, tokens, cost, % of total
   - Sort by cost desc

5. **Model breakdown table** (full width, top 20 models)

6. **Event log** (paginated)
   - Timestamp, user, channel, model, tokens, cost, session/run links
   - Export CSV button -> `GET /api/usage/export`

Reuse components from `frontend/src/components/usage/`; add admin-only wrappers
in `frontend/src/components/admin/usage/`.

## Step 4: Admin sidebar nav

Update admin nav (Flexy `MenuItems` or equivalent):

```typescript
{
  title: 'LLM usage',
  href: '/dashboard/usage',
  icon: 'IconChartBar',
}
```

Place under Agent or Operations group after Conversations.

## Step 5: Budget alert notifications

When month-to-date spend crosses `alert_threshold_percent`:

1. Create in-app notification via `backend/notifications/` store:
   - Type: `llm_budget_alert`
   - Title: "LLM spend approaching monthly budget"
   - Link: `/dashboard/usage`

2. Optional: emit Scout governance event if connector enabled (do not require Scout)

3. Debounce: at most one alert per workspace per calendar month per threshold
   crossing (do not spam on every request)

Check budget on each `LlmUsageRecorder.record` async task or hourly cron; prefer
cron to avoid hot-path overhead.

## Step 6: Settings shortcut

`frontend/src/app/(workspace)/settings/page.tsx` or admin settings:

Link card: "LLM usage and budgets" -> `/dashboard/usage` (admin) or `/usage` (user).

## Step 7: Compare with evals page

Update `frontend/src/app/(workspace)/evals/page.tsx` related surfaces:

Add card linking to `/usage` for operational cost (evals = quality, usage = spend).

## Step 8: Tests

`tests/usage/test_admin_usage.py`:

1. Admin can set budget; non-admin PUT returns 403
2. Dashboard stats include `llmSpend30d`
3. Budget alert creates notification once when threshold crossed (mock)

`tests/frontend/test_admin_usage_dashboard.py`:

1. Admin usage page renders budget form
2. Export button triggers download URL
3. User breakdown table headers present

## Acceptance Criteria

- `/dashboard/usage` shows instance-wide LLM analytics
- Admin overview shows LLM spend stat card linking to usage page
- Monthly budget editable and persisted
- Alert notification fires once when threshold exceeded (test proves)
- CSV export downloads from admin page
- Non-admin cannot access `/dashboard/usage` (redirect or 403)
- `pnpm build` and usage tests pass

## Archive Checklist

Move to `prompts-archive/` and update audit + completed README.

When Prompt 148 archives, the LLM usage series (144-148) is complete. Keep **144**
as permanent reference in `pending-prompts/`.
