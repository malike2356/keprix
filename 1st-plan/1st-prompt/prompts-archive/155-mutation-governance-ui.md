# Keprix - Prompt 155: Mutation Governance UI

## Purpose

Build the operator-facing dashboard for reviewing, approving, rejecting, and
rolling back all four tiers of mutation. The UI surfaces the pending approval
queue, the full mutation history, quality trends for each generated tool,
deployment divergence metrics, and the self-coding diff review panel. After
this prompt, operators have complete visibility and control over everything
Keprix has mutated or is proposing to mutate.

---

## Dependencies

| Prompt | Capability needed |
|---|---|
| 149 | `mutation_events` schema, API shape |
| 150 | Tool synthesis API |
| 151 | Gap-to-synthesis pipeline API: `/api/mutation/tools/*` |
| 152 | Prompt mutation API: `/api/mutation/prompts/*`, `/api/mutation/personas/*` |
| 153 | Code mutation API: `/api/mutation/code/*` |
| 154 | Quality API: `/api/mutation/quality/*`, `/api/mutation/compounding`, prune API |
| existing | Admin shell, nav, SWR patterns from Prompt 116/118 |

---

## Routes and Components

### Route: `/dashboard/mutation`

Main mutation governance page. Entry in admin sidebar under "Agent" or "Operations".

Layout:

```
[Divergence Score Card] [Pending Approvals Count] [Active Tools Count] [Evolved Prompts Count]

Tabs: [ Pending (N) ] [ Tools ] [ Prompts ] [ Code ] [ History ]
```

#### Tab: Pending

The approval queue. Show all mutations with `status="staged"`, newest first.

Each row:
```
[Type pill: TOOL | PROMPT | CODE] [Name] [Trigger] [Confidence] [Age] [Approve] [Reject]
```

Clicking a row expands the detail panel inline:
- For TOOL: show synthesized Python source with syntax highlighting, sandbox
  result summary ("Sandbox: passed"), inferred schema fields.
- For PROMPT: show a side-by-side diff of before/after prompt text.
- For CODE: show unified diff with syntax highlighting, test run output
  (pass/fail badge with full test output collapsible).

Approve/Reject buttons call the respective API endpoints with SWR revalidation.
Bulk approve and bulk reject buttons for selecting multiple staged items.

#### Tab: Tools

All generated tool mutations (any status), paginated 20/page.

Columns: Name | Status | Quality Score | Uses | Last Used | Age | Created By | Actions

Status badges:
- `approved` -> green
- `staged` -> yellow
- `quarantined` -> red
- `pruned` -> gray
- `promoted` -> purple star

`Quality Score` renders as a mini bar (0-100%) colored green/yellow/red by value.

Actions column: View source | Rollback (for approved) | Approve (for staged) | Reject (for staged).

Clicking "View source" opens a slide-over panel with:
- Full Python source (syntax highlighted, read-only)
- Quality history chart: sparkline of score over last N uses
- Use count and last used timestamp
- Sandbox result from original validation

#### Tab: Prompts

All prompt mutation versions, grouped by prompt_key. Each group shows:
- Current active version (highlighted)
- History entries (older versions)

Each version row:
- Version number | Created by | Created at | Status | Diff button | Activate | Rollback

"Diff" opens a side-by-side diff panel comparing this version to the previous one.
"Activate" is only available for non-active versions (re-activates an older version).
"Rollback" available on the current active version only.

Persona overrides shown as a collapsible section below each persona's name.

#### Tab: Code

All code mutations (`tier="code"`), paginated.

Columns: Task description | Branch | Status | Tests | Files changed | Age | Actions

Status badges as before. Tests column: green check / red X / gray dash (pending).

Actions: View diff | View test output | Approve (merge branch) | Reject (delete branch) | Rollback.

Clicking "View diff" opens a full-page diff viewer with syntax highlighting per
file, collapsible per-file sections, and a file list sidebar.

Approve shows a confirmation modal:
```
Merge mutation branch into main?
  Branch: mutation/2026-07-06/add-weather-tool
  Files: src/keprix/tools/weather_tool.py (+127 lines)
  Tests: 42/42 passed
  [Cancel]  [Merge and Approve]
```

#### Tab: History

All mutations across all tiers, combined timeline, newest first.
Filterable by tier, status, date range, and trigger.

Columns: Time | Tier | Name | Trigger | Status | Quality | Actions

---

### Route: `/dashboard/mutation/[id]`

Detail page for a single mutation record. Shows all fields from `mutation_events`
plus quality history chart, quality samples table, and related mutation records
(e.g., the rollback record if it was rolled back).

---

### Components

#### `frontend/src/components/mutation/MutationApprovalPanel.tsx`

Reusable approve/reject panel used in the Pending tab and inline in the Tools,
Prompts, and Code tabs. Props: `mutationId`, `tier`, `onApproved`, `onRejected`.

Calls `POST /api/mutation/tools/{id}/approve` or `/prompts/{key}/approve` or
`/code/{id}/approve` depending on tier. Shows loading spinner during API call.
Renders inline error if the API returns an error.

#### `frontend/src/components/mutation/MutationQualityBadge.tsx`

Displays a quality score as a colored badge with a mini sparkline.
Props: `score: number | null`, `useCount: number`, `status: string`.
Color: green >= 0.75, yellow >= 0.45, red < 0.45, gray for null/staged.

#### `frontend/src/components/mutation/GeneratedToolCard.tsx`

Card showing a single generated tool. Used in the Tools tab row expansion and
in the tool browser. Shows: name, description, quality badge, use count,
last used, source preview (first 10 lines), and action buttons.

#### `frontend/src/components/mutation/DiffViewer.tsx`

Unified diff renderer with syntax highlighting per language (Python, YAML, Markdown).
Shows added lines in green, removed lines in red, unchanged lines in gray.
Collapsible per-file sections with file path headers.
Uses a lightweight diff rendering library (no external dependency; render the
raw unified diff format as structured HTML).

#### `frontend/src/components/mutation/MutationHistoryTable.tsx`

Reusable paginated table for mutation history. Props: filter controls, data.
Used in the History tab and the single-record detail page.

#### `frontend/src/components/mutation/CompoundingMetricsCard.tsx`

Displays `CompoundingMetrics` as a card. Shows:
- Divergence score as a circular progress gauge (0-100%)
- Active mutations count
- Promoted tools count
- Prompt evolutions count
- Code merges count
Links to `/dashboard/mutation` for the full view.

Used on the admin overview `/dashboard` page alongside existing stat cards.

---

### `frontend/src/lib/mutation-api.ts`

SWR-ready API client for all mutation endpoints.

```typescript
export function useMutationQueue(status?: string, tier?: string)
export function useGeneratedTools(page: number, status?: string)
export function usePromptVersions(promptKey: string)
export function useCodeMutations(page: number)
export function useMutationHistory(filters: MutationHistoryFilters)
export function useMutationDetail(id: string)
export function useQualityHistory(mutationId: string)
export function useCompoundingMetrics()

export async function approveMutation(id: string, tier: string): Promise<void>
export async function rejectMutation(id: string, tier: string, reason: string): Promise<void>
export async function rollbackMutation(id: string, tier: string): Promise<void>
export async function triggerSynthesis(toolName: string, description: string): Promise<{mutation_id: string}>
export async function triggerPrune(dryRun: boolean): Promise<PruneReport>
```

---

### Navigation

Add to admin sidebar nav (`frontend/src/lib/navigation.ts`):

```typescript
{
  label: "Mutation",
  href: "/dashboard/mutation",
  icon: "..." // DNA or refresh icon
  badge: pendingCount > 0 ? String(pendingCount) : undefined,
}
```

The badge shows the count of staged mutations awaiting approval. Fetch via
`GET /api/mutation/stats` and display `stats.staged` count. Update on a
30-second SWR interval.

---

### Admin overview additions

On `/dashboard` (admin overview), add:
1. `CompoundingMetricsCard` in the stats row showing divergence score.
2. A "Pending Mutations" alert banner when `stats.staged > 0`:
   ```
   N mutations awaiting approval.  [Review]
   ```

---

## Acceptance Criteria

1. `/dashboard/mutation` renders with all five tabs. Pending tab shows the
   correct count of staged mutations.

2. Clicking "Approve" on a staged tool mutation in the Pending tab calls
   `POST /api/mutation/tools/{id}/approve`, revalidates the list, and moves
   the item out of the Pending tab.

3. The diff viewer renders a unified diff of a Python file with syntax
   highlighting (added lines green, removed lines red).

4. The Code tab "Merge and Approve" modal shows branch name, files changed
   count, and test pass/fail before confirmation.

5. Quality sparklines display correctly for tools with 5+ quality samples.

6. The admin overview `/dashboard` shows the `CompoundingMetricsCard` and
   the "Pending Mutations" alert banner when staged count > 0.

7. The admin sidebar shows a badge with the pending count when > 0.

8. `/dashboard/mutation/[id]` shows all fields for a single mutation including
   quality history.

9. Filtering the History tab by tier="tool" shows only tool mutations.

10. Bulk approve selects multiple rows and calls approve in sequence, with
    a progress indicator.

---

## Tests

### `tests/frontend/test_mutation_dashboard.tsx` (React Testing Library or Playwright)

```
renders pending tab with correct count
approve button calls api and removes item from pending list
reject button with reason calls api
diff viewer renders added lines in green
code tab shows merge confirmation modal
quality badge renders correct color for score 0.8
quality badge renders gray for null score
history tab filters by tier
compounding metrics card renders divergence score
admin overview shows pending alert banner when staged > 0
```

---

## What This Prompt Does NOT Do

- It does not add end-user-facing mutation visibility. Only operators (admin role)
  see the mutation dashboard.
- It does not add a conversational interface for requesting mutations from chat.
  That is a future playbook wrapper around the API.
- It does not add mutation export or portability across deployments.
- It does not add A/B testing of prompt versions.
