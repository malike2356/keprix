# Keprix - Prompt 147: LLM Usage Workspace Dashboard

## Context

Read `144-llm-usage-analytics-wiring-outline.md`.

Complete Prompts **145** and **146** first (API must exist).

This prompt builds the **workspace-facing usage dashboard** so instance users and
owners can monitor their LLM token consumption and estimated cost in the web UI.

Output: `frontend/src/app/(workspace)/usage/`,
`frontend/src/lib/usage-api.ts`, `frontend/src/components/usage/`, tests.

Depends on Prompt **103** (theme, cards) and **136** (workspace layout patterns).

## Step 1: API client

`frontend/src/lib/usage-api.ts`:

```typescript
export type UsageSummary = { ... };
export type UsageTimeseriesPoint = { ... };
export type UsageBreakdownRow = { ... };
export type UsageBudgetStatus = { ... };

export async function fetchUsageSummary(params?: UsageQueryParams): Promise<UsageSummary>;
export async function fetchUsageTimeseries(params?: UsageQueryParams): Promise<UsageTimeseriesPoint[]>;
export async function fetchUsageBreakdown(dimension: "model" | "provider" | "channel", params?: UsageQueryParams): Promise<UsageBreakdownRow[]>;
export async function fetchUsageBudget(): Promise<UsageBudgetStatus>;
```

Use SWR keys like `usage-summary-30`, `usage-timeseries-30-day`.

## Step 2: Page route

`frontend/src/app/(workspace)/usage/page.tsx`

Layout:

```
PageHeader
  title: LLM usage and cost
  description: Token consumption and estimated spend for your account.

PeriodToolbar (7d | 30d | 90d)

Grid: 4 StatCards
  Total tokens
  Estimated cost (USD)
  API calls
  Avg cost per call

Grid 2-col (md):
  UsageTimeseriesChart (tokens + cost toggle)
  UsageModelBreakdownChart (horizontal bar or donut)

RecentUsageTable
  columns: Time, Model, Channel, Tokens, Cost, Session
  session column links to /chat/{sessionId} when present
```

Empty state when no events:

```
No LLM usage recorded yet
Usage appears after you send messages in chat or run agent workflows.
[Open chat]
```

## Step 3: Components

`frontend/src/components/usage/`:

| Component | Responsibility |
| --- | --- |
| `UsageStatCard.tsx` | Wraps admin StatCard or shared metric card |
| `UsagePeriodToolbar.tsx` | Period chips + persists to localStorage |
| `UsageTimeseriesChart.tsx` | ApexCharts line chart (reuse admin chart theme) |
| `UsageModelBreakdownChart.tsx` | Bar or donut with legend |
| `UsageRecentTable.tsx` | MUI Table with compact rows |
| `UsageBudgetBanner.tsx` | Warning when >80% of monthly budget |

Chart colors: use `keprixTheme` palette; support dark mode via ThemeRegistry.

## Step 4: Cost display rules

- Show cost with 4 decimal places when < $1, else 2 decimal places
- When `cost_status` is `unknown`, show em dash and tooltip "Pricing unavailable for this model"
- When `cost_status` is `included`, show `$0.00` with tooltip "Included in subscription"
- Never show raw API keys or provider secrets in UI

## Step 5: Navigation

Update:

- `frontend/src/lib/navigation.ts`: add under `automations` or `admin` group:

```typescript
{ id: "usage", label: "LLM usage", href: "/usage", icon: "monitoring", group: "automations" }
```

- `src/keprix/ui_contract/navigation.py`: matching `NAV_ITEMS` entry
- Launcher hub card optional: "LLM usage" quick link

## Step 6: Chat status bar hook (optional)

`frontend/src/components/workspace/ChatStatusBar.tsx`:

- Small text under model selector: "Session cost: $0.02" when session-level
  summary endpoint exists or client accumulates from stream metadata
- If no per-session API yet, skip without stub; document as follow-up

## Step 7: Frontend tests

`tests/frontend/test_usage_dashboard.py`:

1. Page renders stat card labels
2. Mock API returns summary; values appear in DOM
3. Period toolbar changes SWR key (mock fetch call count)
4. Empty state when summary request_count is 0
5. Navigation includes `/usage` href

## Step 8: Accessibility

- Charts have text alternative table toggle or data summary for screen readers
- Stat cards use semantic headings
- Respect `prefers-reduced-motion` (static table fallback)

## Acceptance Criteria

- `/usage` loads without error when backend has zero events (empty state)
- `/usage` shows real data when events exist (manual or seeded test DB)
- Period selector refetches summary and charts
- Model breakdown lists models from API
- Recent table links to chat sessions when `session_id` set
- `pnpm build` passes
- Nav item visible in workspace sidebar/launcher

## Archive Checklist

Move to `prompts-archive/` and update audit + completed README.
