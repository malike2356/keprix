# Keprix Prompt 168: Skeleton loading 01 - shared primitives

## Purpose

Introduce **reusable skeleton components** and an `AsyncView` wrapper so pages stop
inventing one-off MUI `Skeleton` blocks. Upgrade shared UI components that many routes
depend on (`DataTable`, `RecordDetail`, etc.).

Depends on reference **167** (`prompts-archive/ref-167-skeleton-loading-architecture.md`).

**Out of scope:** Migrating every workspace page (Prompt 169). Admin refactor to
primitives (Prompt 170).

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## What to build

### 1. `frontend/src/components/ui/loading/` module

Create these client components (one file each or sensible grouping):

| Component | Props (minimum) | Renders |
| --- | --- | --- |
| `SkeletonBlock` | `height`, `width?`, `sx?` | Single rounded block; respects reduced motion |
| `SkeletonText` | `lines` (default 3) | Stacked lines with last line shorter |
| `SkeletonList` | `rows` (default 5), `rowHeight?` (default 72) | Vertical stack of row skeletons |
| `SkeletonTable` | `rows`, `columns` (default 4) | Table-shaped placeholder inside `TableContainer` |
| `SkeletonStatGrid` | `count` (default 4) | Grid of stat-card-sized blocks (~120px) |
| `SkeletonChart` | `height?` (default 280) | Chart panel placeholder |
| `SkeletonDetailPanel` | `fields?` (default 6) | Title bar + field rows for master-detail |
| `AsyncView` | `loading`, `error?`, `skeleton`, `children`, `errorTitle?` | Standard loading / error / content switch |

**`usePrefersReducedMotion`:** small hook in `frontend/src/hooks/usePrefersReducedMotion.ts`
(or colocate in loading module). When true, pass `animation={false}` to all skeletons.

**`SkeletonBlock` example behaviour:**

```tsx
<Skeleton
  variant="rounded"
  animation={reducedMotion ? false : "wave"}
  height={height}
  width={width ?? "100%"}
  sx={{ borderRadius: 1, ...sx }}
/>
```

### 2. Barrel export

`frontend/src/components/ui/loading/index.ts` re-exports all primitives.

### 3. Upgrade shared UI components

Replace spinner/text loading with shape-accurate skeletons:

**`components/ui/DataTable.tsx`**

- When `loading`, render `SkeletonTable` with `rows={6}` and `columns={columns.length}`
  instead of centered `CircularProgress`.

**`components/ui/RecordDetail.tsx`**

- When `loading`, render `SkeletonDetailPanel` instead of `Loading record...` text.

**`components/ui/Timeline.tsx`**

- When `loading`, render `SkeletonList rows={4} rowHeight={64}`.

**`components/ui/CitationList.tsx`**, **`ToolRunTrace.tsx`**

- Replace text loading with `SkeletonList` (3-4 rows).

Do not change empty or error states.

### 4. Refactor one reference page to prove integration

Migrate **`frontend/src/app/(workspace)/tasks/page.tsx`**:

- Replace `Loading tasks...` with `SkeletonList rows={6}` under existing `PageHeader` and tabs.
- Keep error and `EmptyState` paths unchanged.

### 5. Documentation

**`docs/frontend/loading-states.md`** (new; add to MkDocs nav under Frontend or Operations):

- Decision table from reference 167
- Import examples for each primitive
- `AsyncView` usage with SWR

**`/opt/lampp/htdocs/verlox/UI.UX/patterns/skeleton-loading-states.md`** (new):

- Visual spec (heights, row counts, reduced motion)
- Link to Keprix component paths
- Note: slow API is acceptable; layout stability is the goal

### 6. Tests

**`frontend/src/components/ui/loading/loading.test.tsx`** (Vitest):

- `SkeletonTable` renders expected row count
- `AsyncView` shows skeleton when `loading`, children when not
- `usePrefersReducedMotion` returns boolean (mock `matchMedia`)

Run: `cd frontend && pnpm test loading.test.tsx` (or project test command).

## Acceptance criteria

- [ ] `frontend/src/components/ui/loading/*` primitives exist and are exported.
- [ ] `DataTable`, `RecordDetail`, `Timeline`, `CitationList`, `ToolRunTrace` use skeletons.
- [ ] `tasks/page.tsx` uses `SkeletonList` instead of text loading.
- [ ] Reduced motion disables skeleton animation.
- [ ] `docs/frontend/loading-states.md` and UI.UX pattern doc committed.
- [ ] Vitest tests pass for loading module.
- [ ] No new emojis or em/en dashes in added files.

## Verification

```bash
cd frontend && pnpm lint && pnpm type-check
cd frontend && pnpm test -- loading
cd frontend && pnpm dev
# Open /tasks with network throttling; confirm list-shaped skeleton, not text
```

## Dependencies

- Prompt 167 (reference)
- MUI Skeleton (already in project)

## Next

Prompt **169** migrates remaining workspace and settings routes to these primitives.
