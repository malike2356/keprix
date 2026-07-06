# Loading states (skeleton UI)

Keprix uses **shape-accurate skeleton placeholders** while API data loads. Slow responses
are acceptable; layout collapse and blank screens are not.

Reference architecture: `planning/prompts/reference/167-skeleton-loading-architecture.md`.

UI.UX pattern spec: `/opt/lampp/htdocs/verlox/UI.UX/patterns/skeleton-loading-states.md`.

## Module location

```text
frontend/src/components/ui/loading/
  SkeletonBlock.tsx
  SkeletonText.tsx
  SkeletonList.tsx
  SkeletonTable.tsx
  SkeletonStatGrid.tsx
  SkeletonChart.tsx
  SkeletonDetailPanel.tsx
  AsyncView.tsx
  index.ts
```

Import from the barrel:

```tsx
import { AsyncView, SkeletonList, SkeletonTable } from "@/components/ui/loading";
```

## Decision table

| Situation | Use | Avoid |
| --- | --- | --- |
| List of records | `SkeletonList` | Centered `CircularProgress` |
| Table of records | `SkeletonTable` | `Loading items...` text |
| Stat cards / dashboard grid | `SkeletonStatGrid` | One large block |
| Chart or wide panel | `SkeletonChart` | Text-only loading |
| Master-detail pane | `SkeletonDetailPanel` | `Loading record...` |
| Full page data region | Skeleton under `PageHeader` | Full-page spinner |
| Form submit | Button `disabled` + `Saving...` | Page skeleton |
| Chat token stream | Stream indicators | Per-token skeleton |

Keep `PageHeader`, tabs, and filters visible during load. Skeleton only the data region.

## Primitives

### `SkeletonBlock`

Single rounded block. Base primitive; respects `prefers-reduced-motion`.

```tsx
<SkeletonBlock height={120} />
<SkeletonBlock height={16} width="60%" />
```

### `SkeletonText`

Stacked lines; last line shorter (default 3 lines).

```tsx
<SkeletonText lines={4} />
```

### `SkeletonList`

Vertical row placeholders (default 5 rows, 72px height).

```tsx
<SkeletonList rows={6} rowHeight={72} />
```

### `SkeletonTable`

Table inside `TableContainer` (default 6 rows, 4 columns).

```tsx
<SkeletonTable rows={8} columns={5} />
```

### `SkeletonStatGrid`

Responsive grid of stat-card blocks (~120px tall).

```tsx
<SkeletonStatGrid count={4} />
```

### `SkeletonChart`

Chart panel placeholder (default height 280).

```tsx
<SkeletonChart height={280} />
```

### `SkeletonDetailPanel`

Title, status pill, field rows, action buttons.

```tsx
<SkeletonDetailPanel fields={6} />
```

### `AsyncView`

Standard loading / error / content switch.

```tsx
const { data, isLoading, error } = useSWR("tasks", fetchTasks);

return (
  <AsyncView
    loading={isLoading}
    error={error?.message}
    errorTitle="Could not load tasks"
    skeleton={<SkeletonList rows={6} />}
  >
    <TaskList tasks={data ?? []} />
  </AsyncView>
);
```

## Reduced motion

`usePrefersReducedMotion` (`frontend/src/hooks/usePrefersReducedMotion.ts`) disables
skeleton wave animation when the user prefers reduced motion.

## Shared components (upgraded in Prompt 168)

| Component | Loading UI |
| --- | --- |
| `DataTable` | `SkeletonTable` |
| `RecordDetail` | `SkeletonDetailPanel` |
| `Timeline` | `SkeletonList` (4 rows) |
| `CitationList` | `SkeletonList` (4 rows) |
| `ToolRunTrace` | `SkeletonList` (3 rows) |

## Reference page

`/tasks` uses `SkeletonList rows={6}` under tabs while `fetchTasks` runs.

## Migration status

| Batch | Prompt | Status |
| --- | --- | --- |
| Primitives + shared UI | 168 | Shipped |
| Workspace / settings pages | 169 | Shipped |
| Admin normalization + CI contract | 170 | Shipped |

Series prompts: **167** (architecture), **168** (primitives), **169** (workspace), **170** (admin + contract).
Archived under `planning/prompts/prompts-archive/completed/`.

### Batch A: Workspace core (169)

| File | Primitive |
| --- | --- |
| `notes/page.tsx` | `SkeletonList` |
| `documents/page.tsx` | `SkeletonList` + `SkeletonDetailPanel` |
| `contacts/page.tsx` | `SkeletonList` |
| `contacts/[id]/page.tsx` | `SkeletonDetailPanel` |
| `contacts/preferences/page.tsx` | `SkeletonDetailPanel` |
| `vault/page.tsx` | `SkeletonTable` |
| `calendar/page.tsx` | `SkeletonList` |
| `email/page.tsx` | `SkeletonList` + `SkeletonDetailPanel` |
| `memory/page.tsx` | `SkeletonTable` |
| `skills/page.tsx` | `SkeletonTable` |
| `gallery/page.tsx` | `SkeletonBlock` grid |
| `tasks/page.tsx` | `SkeletonList` (168) |

### Batch B: Settings and billing (169)

| File | Primitive |
| --- | --- |
| `settings/billing/page.tsx` | `SkeletonDetailPanel` |
| `BillingSettingsContent.tsx` | `SkeletonStatGrid` + `SkeletonTable` |
| `BillingSeatsPanel.tsx` | `SkeletonList` |
| `BillingInvoiceTable.tsx` | `SkeletonTable` |
| `BillingSubscriptionSummary.tsx` | `SkeletonDetailPanel` |
| `settings/governance/page.tsx` | `SkeletonDetailPanel` |
| `settings/users/page.tsx` | `SkeletonTable` |
| `WorkspaceUsersManager.tsx` | `SkeletonTable` |
| `settings/web-search/page.tsx` | `SkeletonList` |
| `settings/localization/metrics/page.tsx` | `SkeletonStatGrid` + `SkeletonChart` |
| `settings/localization/corrections/page.tsx` | `SkeletonDetailPanel` (dialog) |
| `settings/voice-templates/[id]/page.tsx` | `SkeletonDetailPanel` |

### Batch C: Feature workspaces (169)

| File | Primitive |
| --- | --- |
| `research/page.tsx` | `LinearProgress` only (job progress) |
| `analytics/page.tsx` | `SkeletonChart` + `SkeletonTable` while analyzing |
| `compare/page.tsx` | `SkeletonStatGrid` + column `SkeletonBlock` |
| `opportunities/[id]/page.tsx` | `SkeletonDetailPanel` |
| `playbook/page.tsx` | `SkeletonStatGrid` |
| `PersonaSelector.tsx` | `SkeletonBlock` grid |
| `RepoMapPanel.tsx` | `SkeletonChart` |
| `OpportunityArtifactViewer.tsx` | `SkeletonDetailPanel` |

### Batch D: Shell and auth (169)

| File | Primitive |
| --- | --- |
| `AppShell.tsx` | `SkeletonText` |
| `auth/login/page.tsx` | `SkeletonDetailPanel` (Suspense) |
| `auth/accept-invite/page.tsx` | `SkeletonDetailPanel` |

Deferred to Prompt **170**: admin dashboard widgets, `admin/mcp`, `admin/backup`, `admin/cron`, chat bootstrap spinner.

### Batch E: Admin and usage (170)

| File | Primitive |
| --- | --- |
| `components/admin/*` widgets | `SkeletonBlock`, `SkeletonChart`, `SkeletonTable`, `SkeletonList` |
| `components/admin/usage/*`, `components/usage/*` | Matching chart/table primitives |
| `components/mutation/CompoundingMetricsCard.tsx` | `SkeletonBlock` (loading) |
| `components/mutation/MutationHistoryTable.tsx` | `SkeletonTable` |
| `(admin)/dashboard/mutation/[id]/page.tsx` | `SkeletonDetailPanel` |
| `(admin)/dashboard/settings/page.tsx` | `SkeletonDetailPanel` |
| `admin/teams/page.tsx` | `SkeletonList` |
| `admin/tools/page.tsx` | `SkeletonBlock` + `SkeletonTable` |
| `admin/mcp/page.tsx` | `SkeletonList` |
| `admin/backup/page.tsx` | `SkeletonDetailPanel` |
| `admin/cron/page.tsx` | `SkeletonTable` |
| `developer/page.tsx`, `developer/sdk/page.tsx` | Primitives throughout |
| `components/developer/OpenApiExplorer.tsx` | `SkeletonDetailPanel` |
| `notifications/page.tsx` | `SkeletonList` |

Allowed spinners: `chat/page.tsx` (bootstrap), `analytics/page.tsx` (upload), button actions with `@loading-contract-ignore`.

## Tests

```bash
cd frontend && pnpm test -- loading
cd .. && .venv/bin/python -m pytest tests/ui/test_loading_contract.py -q
```

CI runs `tests/ui/test_loading_contract.py` via the backend pytest job.
