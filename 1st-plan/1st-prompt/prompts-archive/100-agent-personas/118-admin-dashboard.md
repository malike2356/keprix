# Keprix Prompt 118: Admin Dashboard

**Status:** Completed 2026-07-06. Evidence: `/admin/dashboard` rewrites, `admin-dashboard-api.ts`, stat cards, charts, staged alert.

## Purpose

Complete the Keprix admin dashboard so an operator can see at a glance: agent activity,
conversation volume, mutation (tool synthesis) throughput, LLM cost, channel health, and
recent events. The dashboard page and all stat/chart components are already scaffolded - this
prompt makes them real: live data from the backend, working charts, and functional sub-pages.

The admin area lives at `/admin/dashboard` and is protected by `useRequireSession()`.

---

## Dependencies

- `frontend/src/app/(admin)/dashboard/page.tsx` (exists, full scaffolding with all SWR fetchers)
- `frontend/src/app/(admin)/layout.tsx` (exists, AdminSidebar + AdminHeader)
- `frontend/src/components/admin/StatCard.tsx` (exists)
- `frontend/src/components/admin/AgentActivity.tsx` (exists, scaffold)
- `frontend/src/components/admin/ChannelHealthStrip.tsx` (exists, scaffold)
- `frontend/src/components/admin/MutationCompoundingSparkline.tsx` (exists, scaffold)
- `frontend/src/components/admin/RecentConversations.tsx` (exists, scaffold)
- `frontend/src/components/admin/RecentMutations.tsx` (exists, scaffold)
- `frontend/src/components/admin/ToolSynthesisBreakup.tsx` (exists, scaffold)
- `frontend/src/lib/admin-dashboard-api.ts` (exists, all fetcher functions scaffolded)
- `frontend/src/lib/admin-api.ts` (exists)
- `frontend/src/lib/mutation-api.ts` (exists, `useMutationStats`, `useCompoundingMetrics`)
- Backend admin API: `GET /api/admin/stats`, `GET /api/admin/conversations/daily`,
  `GET /api/admin/mutations/daily`, `GET /api/admin/tools/breakdown`,
  `GET /api/admin/channels/status`
- `ApexCharts` available via `react-apexcharts` (in package.json)
- Prompt 116 complete (theme)

---

## What to build

### 1. Implement `admin-dashboard-api.ts`

**`frontend/src/lib/admin-dashboard-api.ts`** (EDIT - fill in real fetch logic)

Each function already has a signature; add the `ceApi` call and shape the response.

```ts
import { ceApi } from "@/lib/ce-api";

export type DashboardStats = {
  total_conversations: number;
  active_agents: number;
  tools_synthesised: number;
  llm_cost_usd_mtd: number;
  conversations_today: number;
  mutations_pending_review: number;
};

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const res = await ceApi("/api/admin/stats");
  if (!res.ok) throw new Error("Failed to fetch dashboard stats");
  return res.json();
}

export type DailyPoint = { date: string; count: number };

export async function fetchConversationDaily(): Promise<DailyPoint[]> {
  const res = await ceApi("/api/admin/conversations/daily?days=30");
  if (!res.ok) throw new Error("Failed to fetch conversation daily");
  return res.json();
}

export async function fetchMutationActiveDaily(): Promise<DailyPoint[]> {
  const res = await ceApi("/api/admin/mutations/daily?days=30");
  if (!res.ok) throw new Error("Failed to fetch mutation daily");
  return res.json();
}

export type ToolBreakdownRow = { tool_name: string; call_count: number; success_rate: number };

export async function fetchToolBreakdown(): Promise<ToolBreakdownRow[]> {
  const res = await ceApi("/api/admin/tools/breakdown?limit=8");
  if (!res.ok) throw new Error("Failed to fetch tool breakdown");
  return res.json();
}

export type RecentMutation = {
  id: string;
  name: string;
  status: "approved" | "staged" | "rejected";
  created_at: string;
  workspace_id: string;
};

export async function fetchRecentMutations(limit = 5): Promise<RecentMutation[]> {
  const res = await ceApi(`/api/admin/mutations?limit=${limit}&sort=created_at:desc`);
  if (!res.ok) throw new Error("Failed to fetch recent mutations");
  const data = await res.json();
  return Array.isArray(data) ? data : (data.items ?? []);
}

export type RecentConversation = {
  id: string;
  title: string;
  model: string;
  message_count: number;
  created_at: string;
  user_id: string;
};

export async function fetchRecentConversations(limit = 5): Promise<RecentConversation[]> {
  const res = await ceApi(`/api/admin/conversations?limit=${limit}&sort=created_at:desc`);
  if (!res.ok) throw new Error("Failed to fetch recent conversations");
  const data = await res.json();
  return Array.isArray(data) ? data : (data.items ?? []);
}

export type ChannelStatus = {
  id: string;
  type: string;
  name: string;
  status: "healthy" | "error" | "disconnected";
  last_event_at: string | null;
};

export async function fetchChannelStatus(): Promise<ChannelStatus[]> {
  const res = await ceApi("/api/admin/channels/status");
  if (!res.ok) throw new Error("Failed to fetch channel status");
  return res.json();
}
```

### 2. StatCard - verify it renders correctly

**`frontend/src/components/admin/StatCard.tsx`** (READ and verify)

StatCard already exists. Confirm it:
- Shows a skeleton when `loading` is true
- Shows `delta` with green text when `positive` is true
- Accepts `href` and wraps the card in a `NextLink` when present
- The icon is rendered in a colored circle matching `color` prop

No code change needed if all four conditions are met. Add any missing ones.

The dashboard page passes these stats:

```tsx
// Verify the dashboard wires stats like this:
<StatCard
  title="Conversations"
  value={stats?.total_conversations ?? 0}
  delta={stats ? `${stats.conversations_today} today` : undefined}
  positive
  icon={<IconMessages size={20} />}
  color="primary"
  loading={statsLoading}
  href="/admin/conversations"
/>
<StatCard
  title="Tools synthesised"
  value={stats?.tools_synthesised ?? 0}
  icon={<IconTools size={20} />}
  color="secondary"
  loading={statsLoading}
  href="/admin/mutations"
/>
<StatCard
  title="LLM cost (MTD)"
  value={formatUsdCost(stats?.llm_cost_usd_mtd ?? 0)}
  icon={<IconCurrencyDollar size={20} />}
  color="success"
  loading={statsLoading}
  href="/admin/usage"
/>
<StatCard
  title="Active agents"
  value={stats?.active_agents ?? 0}
  icon={<IconGitBranch size={20} />}
  color="info"
  loading={statsLoading}
/>
```

### 3. AgentActivity - conversation volume chart

**`frontend/src/components/admin/AgentActivity.tsx`** (EDIT)

Replace placeholder with an ApexCharts area chart of conversation count per day over 30 days.

```tsx
"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { SkeletonBlock } from "@/components/ui/loading";
import { useTheme } from "@mui/material/styles";
import type { DailyPoint } from "@/lib/admin-dashboard-api";

const ReactApexChart = dynamic(() => import("react-apexcharts"), { ssr: false });

type AgentActivityProps = {
  data: DailyPoint[] | undefined;
  loading: boolean;
};

export default function AgentActivity({ data, loading }: AgentActivityProps) {
  const theme = useTheme();

  const series = [
    {
      name: "Conversations",
      data: (data ?? []).map((p) => ({ x: p.date, y: p.count })),
    },
  ];

  const options: ApexCharts.ApexOptions = {
    chart: {
      type: "area",
      toolbar: { show: false },
      background: "transparent",
      animations: { enabled: true, speed: 400 },
    },
    theme: { mode: theme.palette.mode },
    stroke: { curve: "smooth", width: 2 },
    fill: {
      type: "gradient",
      gradient: {
        shadeIntensity: 1,
        opacityFrom: 0.35,
        opacityTo: 0.02,
        stops: [0, 90, 100],
      },
    },
    xaxis: {
      type: "datetime",
      labels: { style: { colors: theme.palette.text.secondary, fontSize: "11px" } },
      axisBorder: { show: false },
      axisTicks: { show: false },
    },
    yaxis: {
      labels: {
        style: { colors: theme.palette.text.secondary, fontSize: "11px" },
        formatter: (v: number) => String(Math.round(v)),
      },
    },
    grid: { borderColor: theme.palette.divider, strokeDashArray: 4 },
    tooltip: { theme: theme.palette.mode, x: { format: "dd MMM" } },
    colors: [theme.palette.primary.main],
    dataLabels: { enabled: false },
  };

  if (loading) return <SkeletonBlock height={200} />;

  return (
    <Box>
      <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600 }}>
        Conversation volume (30 days)
      </Typography>
      <ReactApexChart type="area" series={series} options={options} height={200} />
    </Box>
  );
}
```

### 4. MutationCompoundingSparkline

**`frontend/src/components/admin/MutationCompoundingSparkline.tsx`** (EDIT)

Sparkline bar chart: mutation approvals per day. Same ApexCharts pattern as AgentActivity but
using `type: "bar"` with `secondary.main` color and height 140.

```tsx
// series: mutation daily data
// title: "Tool synthesis (30 days)"
// color: theme.palette.secondary.main
// chart type: "bar"
// height: 140
// Matches the AgentActivity pattern exactly, substitute the color and series.
```

### 5. ToolSynthesisBreakup

**`frontend/src/components/admin/ToolSynthesisBreakup.tsx`** (EDIT)

Horizontal bar chart showing top-8 tools by call count.

```tsx
// series: [{ name: "Calls", data: rows.map(r => r.call_count) }]
// xaxis.categories: rows.map(r => r.tool_name)
// chart type: "bar"
// plotOptions: { bar: { horizontal: true, barHeight: "70%" } }
// colors: [theme.palette.primary.main]
// height: 240
```

Show `success_rate` as a secondary label on each bar if space allows (tooltip is fine).

### 6. RecentMutations

**`frontend/src/components/admin/RecentMutations.tsx`** (EDIT)

A `Table` (or list of `ListItem`) showing the 5 most recent mutations with columns:
Name, Status chip, Created (relative time), Workspace.

```tsx
// Status chip colors:
// approved -> success
// staged -> warning
// rejected -> error

// "created_at" formatted with date-fns or native:
// new Intl.RelativeTimeFormat("en", { numeric: "auto" })

// Each row: clicking navigates to /admin/mutations?id={mutation.id}
```

Import `timeAgo` from `@/lib/time-ago` (if it exists) or use a simple inline helper.

### 7. RecentConversations

**`frontend/src/components/admin/RecentConversations.tsx`** (EDIT)

Same pattern as RecentMutations but for conversations. Columns: Title, Model, Messages, Created.
Clicking navigates to `/admin/conversations?id={conversation.id}`.

### 8. ChannelHealthStrip

**`frontend/src/components/admin/ChannelHealthStrip.tsx`** (EDIT)

A horizontal strip of colored dots: one per connected channel. Dot colors:
- `success.main` for healthy
- `error.main` for error
- `text.disabled` for disconnected

```tsx
// Layout: flex row, gap 2, each item: dot + channel name + type label
// "No channels connected" empty state if array is empty with a link to /admin/settings/channels
```

### 9. Admin sub-pages: Navigation and placeholders

**`frontend/src/components/admin/Sidebar.tsx`** (READ and verify nav links)

Verify the admin sidebar contains links to all of these routes. Add any that are missing:
- `/admin/dashboard` - Dashboard
- `/admin/conversations` - Conversations
- `/admin/mutations` - Mutations
- `/admin/models` - Models
- `/admin/usage` - Usage
- `/admin/users` - Users
- `/admin/channels` - Channels
- `/admin/billing` - Billing
- `/admin/settings` - Settings

### 10. Models admin page

**`frontend/src/app/(admin)/models/page.tsx`** (NEW or EDIT if scaffolded)

Table of configured LLM providers. Each row: Provider name, model ID, type (chat/embed),
enabled toggle, cost (input/output per 1M tokens), delete button.

Data from `GET /api/admin/models` via `ceApi`. Use SWR. On toggle `enabled`, call
`PATCH /api/admin/models/{id}` with `{ enabled: boolean }`. Show a Snackbar on success/error.

```tsx
// columns: Provider, Model ID, Type, Enabled, Input cost, Output cost, Actions
// "Add model" button opens a Dialog with a form (Provider select, model ID text, API key text,
//  input/output cost number fields, type select)
// On submit: POST /api/admin/models with the form data
```

### 11. Mutations admin page

**`frontend/src/app/(admin)/mutations/page.tsx`** (NEW or EDIT if scaffolded)

Table of all synthesised tools with filters (status: all / staged / approved / rejected).

Each row: Tool name, Status chip, Workspace, Lines of code, Created, Actions.
Actions for `staged` rows: "Review" button that opens a drawer showing the full Python code diff
with syntax highlighting (use `@/components/admin/ToolDetailDrawer.tsx` which is already
scaffolded).

Approval flow:
- "Approve" button: `POST /api/mutations/{id}/approve`
- "Reject" button: `POST /api/mutations/{id}/reject`
- Both update the row optimistically via `mutate()` from useSWR.

### 12. Usage admin page

**`frontend/src/app/(admin)/usage/page.tsx`** (NEW or EDIT if scaffolded)

LLM cost dashboard. Components:
- Budget status card (current month spend / budget / percent bar) from
  `GET /api/admin/budget/status`
- Cost by model (donut chart, ApexCharts) from `GET /api/admin/usage/by-model`
- Daily cost chart (area chart) from `GET /api/admin/usage/daily?days=30`
- Budget settings form: set `monthly_budget_usd` and `alert_threshold_percent`, saved via
  `PUT /api/admin/budget`

### 13. Alert banner for staged mutations

**`frontend/src/app/(admin)/dashboard/page.tsx`** (EDIT - verify alert banner exists)

The dashboard page already has a staged-mutation alert:
```tsx
{stagedCount > 0 ? (
  <Alert severity="warning" action={<Button component={NextLink} href="/admin/mutations?status=staged">Review</Button>}>
    {stagedCount} tool{stagedCount !== 1 ? "s" : ""} awaiting your approval.
  </Alert>
) : null}
```

Verify this renders correctly when `mutationStats.staged > 0`.

### 14. Acceptance test (manual)

After implementing:

1. Navigate to `http://localhost:3000/admin/dashboard` (redirects to `/login` if not authed).
2. After login, the dashboard shows 4 stat cards, conversation area chart, mutation sparkline,
   tool synthesis bar chart, recent mutations table, recent conversations table, channel health.
3. All charts render without "window is not defined" SSR errors (dynamic import with ssr: false).
4. If the backend has data, charts show real numbers. If not, they show zeros gracefully (no crash).
5. The staged mutations alert appears when the backend returns `staged > 0`.
6. Clicking "Review" in the alert navigates to `/admin/mutations?status=staged`.
7. The Mutations page shows a table and "Approve"/"Reject" buttons work (Snackbar confirmation).
8. The Models page shows the model list and the enabled toggle works.
