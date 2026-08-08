# Keprix Prompt 170: Skeleton loading 03 - admin normalization and enforcement

## Purpose

Normalize **admin dashboard** skeleton usage onto shared primitives, add **regression
guards**, and close the loading-states documentation loop.

Depends on Prompts **168** and **169**.

After this prompt, ad-hoc `Skeleton variant="rounded" height={220}` copies should be
replaced with `SkeletonChart`, `SkeletonTable`, etc., and CI should catch new
`Loading...` regressions in covered paths.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## What to build

### 1. Refactor admin components to primitives

Replace inline MUI `Skeleton` imports with primitives from `@/components/ui/loading`:

| File | Replace with |
| --- | --- |
| `components/admin/StatCard.tsx` | `SkeletonBlock` height 120 inside `DashboardCard` |
| `components/admin/AgentActivity.tsx` | `SkeletonChart` |
| `components/admin/ChannelHealthStrip.tsx` | `SkeletonBlock` height 72 |
| `components/admin/RecentConversations.tsx` | `SkeletonChart` or `SkeletonList` |
| `components/admin/RecentMutations.tsx` | `SkeletonChart` |
| `components/admin/ToolTable.tsx` | `SkeletonTable` |
| `components/admin/ToolSynthesisBreakup.tsx` | `SkeletonChart` height 180 |
| `components/admin/MutationCompoundingSparkline.tsx` | `SkeletonChart` height 120 |
| `components/admin/usage/*` | Matching primitive per component |
| `components/usage/*` | Matching primitive per component |
| `components/mutation/CompoundingMetricsCard.tsx` | `SkeletonStatGrid` or `SkeletonBlock` |
| `components/mutation/MutationApprovalPanel.tsx` | `SkeletonDetailPanel` |
| `components/mutation/MutationHistoryTable.tsx` | `SkeletonTable` |
| `components/workspace/blocks/MutationCard.tsx` | `SkeletonBlock` |
| `app/(admin)/dashboard/mutation/[id]/page.tsx` | `SkeletonDetailPanel` |
| `app/(admin)/dashboard/settings/page.tsx` | `SkeletonDetailPanel` |
| `app/(workspace)/admin/teams/page.tsx` | `SkeletonChart` |
| `app/(workspace)/admin/tools/page.tsx` | `SkeletonTable` + `SkeletonChart` |
| `app/(workspace)/admin/mcp/page.tsx` | `SkeletonList` |
| `app/(workspace)/admin/backup/page.tsx` | `SkeletonDetailPanel` |
| `app/(workspace)/admin/cron/page.tsx` | `SkeletonTable` |
| `app/(workspace)/developer/page.tsx` | Primitives throughout (many inline skeletons today) |
| `app/(workspace)/developer/sdk/page.tsx` | Primitives throughout |
| `components/developer/OpenApiExplorer.tsx` | `SkeletonDetailPanel` |
| `app/(workspace)/notifications/page.tsx` | `SkeletonList` (already good; switch to primitive) |

Remove duplicate `import Skeleton from "@mui/material/Skeleton"` where no longer needed.

### 2. UI contract test

**`tests/ui/test_loading_contract.py`**

Static analysis (no browser required):

- Parse allowlist/denylist paths under `frontend/src/app/(workspace)` and `frontend/src/components`.
- **Fail** if primary page files match `Loading [a-z]+\.\.\.` (regex) outside allowlist.
- **Fail** if `(workspace)` or `(admin)` page files import `CircularProgress` without
  `@loading-contract-ignore` comment on the same line (escape hatch for button spinners only).
- **Pass** if `components/ui/loading/` exists and exports `AsyncView`, `SkeletonTable`, `SkeletonList`.

Allowlist (initial):

- `chat/page.tsx`, `chat/[sessionId]/page.tsx` (session bootstrap)
- `components/ui/DataTable.tsx` if any spinner remains for secondary actions
- Form submit handlers inside dialogs

Document allowlist in test file header.

Run in CI: add step to `.github/workflows/ci.yml` frontend job or community job:

```bash
.venv/bin/python -m pytest tests/ui/test_loading_contract.py -q
```

### 3. Optional ESLint (stretch)

If feasible without large churn, add `eslint-plugin-local` rule or simple script
`scripts/check-loading-patterns.sh` called from `validate-community-files.sh` or CI.
Not required if pytest contract is thorough.

### 4. Documentation finalization

Update:

- `docs/frontend/loading-states.md`: mark series complete; link prompts 167-170.
- `/opt/lampp/htdocs/verlox/UI.UX/patterns/skeleton-loading-states.md`: add before/after
  screenshots or ASCII wireframes for list/table/chart/detail patterns.
- `planning/prompts/PROMPT-IMPLEMENTATION-AUDIT.md`: row for 167-170.
- `CONTRIBUTING.md` (frontend section if present): mention loading-state rule briefly.

### 5. Agent brief (optional)

`prompts-archive/170-skeleton-loading-verification.md`:

- Throttle network; verify `/dashboard`, `/usage`, `/notifications`, `/vault`.
- Confirm reduced motion disables animation.
- Confirm contract test passes.

## Acceptance criteria

- [ ] Admin and usage components use `@/components/ui/loading` primitives (no stray inline Skeleton except inside primitives module).
- [ ] `tests/ui/test_loading_contract.py` passes and runs in CI.
- [ ] `rg 'from "@mui/material/Skeleton"' frontend/src` only hits `components/ui/loading/` (and zero or documented exceptions).
- [ ] Docs and UI.UX pattern doc updated.
- [ ] Prompts 168-170 archived to `prompts-archive/`.
- [ ] `pnpm lint`, `pnpm type-check`, frontend tests green.

## Verification

```bash
cd frontend && pnpm lint && pnpm type-check && pnpm test
cd /opt/lampp/htdocs/verlox/keprix && .venv/bin/python -m pytest tests/ui/test_loading_contract.py -q
rg 'Loading [a-z]+\.\.\.' frontend/src/app frontend/src/components --glob '*.tsx'
rg 'from "@mui/material/Skeleton"' frontend/src
```

Manual: Chrome Slow 3G on `/dashboard` and `/usage`; layout should not collapse to a single spinner.

## Rollback

If skeleton migration causes layout bugs on a specific page:

- Revert that page only; keep primitives module and contract test.
- Add page to contract allowlist temporarily with a linked issue.

## Dependencies

- Prompt 168 (primitives)
- Prompt 169 (workspace pages)
