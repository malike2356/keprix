# Keprix Prompt 169: Skeleton loading 02 - workspace pages migration

## Purpose

Migrate **workspace, settings, and billing routes** from `Loading...` text and centered
spinners to the shared skeleton primitives shipped in Prompt **168**.

Users should see stable layout on slow API responses across everyday product pages.

Depends on Prompt **168** (`168-skeleton-loading-01-primitives.md`).

**Out of scope:** Admin dashboard widget refactor (Prompt 170). Chat streaming UI.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## What to build

### Migration rules (apply to every file below)

1. Keep `PageHeader` (and tabs/filters) **visible** during load; skeleton only the data region.
2. Use `AsyncView` + appropriate skeleton primitive, or pass `loading` to child components
   that already support it.
3. Remove primary-content `CircularProgress` and `Typography` `Loading ...` strings.
4. Action buttons may still use `disabled` + `Saving...` / `Scanning...` labels.
5. Match skeleton shape to final UI (table vs list vs cards vs detail).

### Batch A: Workspace core (list + CRUD pages)

| File | Skeleton target |
| --- | --- |
| `app/(workspace)/notes/page.tsx` | `SkeletonList` |
| `app/(workspace)/documents/page.tsx` | `SkeletonList` |
| `app/(workspace)/contacts/page.tsx` | `SkeletonList` or `SkeletonTable` |
| `app/(workspace)/contacts/[id]/page.tsx` | `SkeletonDetailPanel` |
| `app/(workspace)/contacts/preferences/page.tsx` | `SkeletonDetailPanel` |
| `app/(workspace)/vault/page.tsx` | `SkeletonTable` |
| `app/(workspace)/calendar/page.tsx` | `SkeletonList` (event rows) |
| `app/(workspace)/email/page.tsx` | `SkeletonList` (replace spinner) |
| `app/(workspace)/memory/page.tsx` | `SkeletonList` |
| `app/(workspace)/skills/page.tsx` | `SkeletonList` |
| `app/(workspace)/gallery/page.tsx` | `SkeletonStatGrid` or card grid skeleton |
| `app/(workspace)/tasks/page.tsx` | Done in 168; verify only |

### Batch B: Settings and billing

| File | Skeleton target |
| --- | --- |
| `app/(workspace)/settings/billing/page.tsx` | `SkeletonDetailPanel` |
| `components/billing/BillingSettingsContent.tsx` | `SkeletonStatGrid` + `SkeletonTable` |
| `components/billing/BillingSeatsPanel.tsx` | `SkeletonList` |
| `components/billing/BillingInvoiceTable.tsx` | `SkeletonTable` |
| `components/billing/BillingSubscriptionSummary.tsx` | `SkeletonDetailPanel` |
| `app/(workspace)/settings/governance/page.tsx` | `SkeletonDetailPanel` |
| `app/(workspace)/settings/users/page.tsx` | `SkeletonTable` |
| `components/users/WorkspaceUsersManager.tsx` | `SkeletonTable` |
| `app/(workspace)/settings/web-search/page.tsx` | `SkeletonList` |
| `app/(workspace)/settings/localization/metrics/page.tsx` | `SkeletonChart` |
| `app/(workspace)/settings/localization/corrections/page.tsx` | `SkeletonTable` |
| `app/(workspace)/settings/voice-templates/[id]/page.tsx` | `SkeletonDetailPanel` |

### Batch C: Feature workspaces (heavier layouts)

| File | Skeleton target |
| --- | --- |
| `app/(workspace)/research/page.tsx` | Replace `CircularProgress` with section skeletons |
| `app/(workspace)/analytics/page.tsx` | `SkeletonChart` + `SkeletonTable` |
| `app/(workspace)/compare/page.tsx` | Column skeletons matching compare layout |
| `app/(workspace)/opportunities/[id]/page.tsx` | `SkeletonDetailPanel` |
| `app/(workspace)/playbook/page.tsx` | `SkeletonStatGrid` for hardware cards (keep button `Scanning...`) |
| `components/agent-studio/PersonaSelector.tsx` | Card grid skeleton (2 columns) |
| `components/coding/RepoMapPanel.tsx` | Normalize to `SkeletonChart` primitive |
| `components/opportunity/OpportunityArtifactViewer.tsx` | `SkeletonDetailPanel` |

### Batch D: Shell and auth (light touch)

| File | Change |
| --- | --- |
| `components/shell/AppShell.tsx` | Replace `Loading workspace context...` with compact `SkeletonText lines={2}` in sidebar header area only |
| `app/auth/login/page.tsx` | Optional: form-sized skeleton if provider list fetch is slow |
| `app/auth/accept-invite/page.tsx` | `SkeletonDetailPanel` inside Suspense fallback |

**Chat (`chat/page.tsx`):** Optional improvement only; do not block this prompt on chat work.

### 2. Shared component consumers

Ensure these use loading props consistently after page migrations:

- `DataTable` (already upgraded in 168)
- `RecordDetail` (already upgraded in 168)
- Any page-local duplicate table/list loading markup removed in favour of primitives

### 3. Update docs

Extend `docs/frontend/loading-states.md` with a **migration checklist** table marking Batch A-D
files as migrated.

## Acceptance criteria

- [ ] Every file in Batch A-C uses skeleton primitives for primary data loading.
- [ ] No `Loading <noun>...` typography remains in migrated files for primary content.
- [ ] No centered `CircularProgress` for primary list/table/chart areas in migrated files.
- [ ] `PageHeader` remains visible during load on all migrated pages.
- [ ] `pnpm lint`, `pnpm type-check` pass in `frontend/`.
- [ ] Manual spot-check: `/tasks`, `/vault`, `/settings/billing`, `/research` with network throttle.

## Verification

```bash
cd frontend && pnpm lint && pnpm type-check
# Grep guard (should trend toward zero in workspace/settings):
rg 'Loading [a-z]+\.\.\.' frontend/src/app/\(workspace\) frontend/src/components/billing
rg 'CircularProgress' frontend/src/app/\(workspace\) --glob '*.tsx'
```

Chrome DevTools: Slow 3G, hard reload on `/vault`, `/calendar`, `/settings/users`.

## Dependencies

- Prompt 168 (primitives must exist)

## Next

Prompt **170** normalizes admin dashboard widgets, adds CI contract tests, and prevents regression.
