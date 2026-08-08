# Keprix - Prompt 224: Workspace Sidebar Collapsible Groups

## Context

Reduce left-pane clutter by making platform navigation **groups collapsible**. Prepares the shell for **installed built apps** (prompt **226**) without stuffing app submodule routes into the global tree.

Depends on **223** (reference). Prerequisite: **136** (workspace), **22** (UI shell).

## Working directory

`/opt/lampp/htdocs/verlox/keprix/frontend/`

## Current behavior

`frontend/src/components/shell/Sidebar.tsx` renders all groups from `navigationFromContract()` as always-expanded overlines + item lists. No persistence.

## Target behavior

| Interaction | Result |
| --- | --- |
| Click group header | Toggle expand/collapse for that group |
| Navigate to a route | Auto-expand the group containing the active item |
| Reload | Restore open/closed state from `localStorage` |
| Default on first visit | `workspace` expanded; all other groups collapsed |

When route matches `/apps/[slug]/*`, also expand group `installed_apps` (stub OK until **226** wires items; use group id constant either way).

## Implementation

### 1. Group header component

Create `frontend/src/components/shell/SidebarNavGroup.tsx`:

- Props: `groupId`, `label`, `expanded`, `onToggle`, `children`
- Header: overline + chevron (`ExpandMore` / `ChevronRight`)
- `role="button"`, `aria-expanded`, keyboard Enter/Space toggles
- Collapsed: hide children, keep header visible

### 2. Persistence hook

Create `frontend/src/hooks/useSidebarGroupState.ts`:

```typescript
const STORAGE_PREFIX = "keprix_nav_group_";

function defaultExpanded(groupId: string, pathname: string): boolean {
  if (groupId === "workspace") return true;
  if (groupId === "installed_apps" && pathname.startsWith("/apps/")) return true;
  return false;
}
```

- Read/write boolean per `groupId`
- On pathname change: call `ensureExpandedForActiveGroup(groups, items, pathname)` without collapsing user-opened groups

### 3. Wire `Sidebar.tsx`

Replace static group `Box` with `SidebarNavGroup`. Keep badges on playbooks / operator-copilot items.

### 4. Mobile drawer

Same collapse behavior in temporary drawer; closing drawer on nav click unchanged.

## Accessibility

- Group headers are focusable buttons
- `aria-controls` pointing at list id `sidebar-group-{groupId}`
- Screen reader label: "{label} navigation group"

## Tests

`frontend/src/components/shell/SidebarNavGroup.test.tsx`:

- Click header toggles `aria-expanded`
- Default expanded for workspace group
- Persistence: expand state survives rerender when localStorage seeded

`tests/frontend/test_built_apps_navigation.py` (stub file in **228**; add one guard here):

- `SidebarNavGroup.tsx` exists
- `useSidebarGroupState` imported from `Sidebar.tsx`

## Out of scope

- Icon-only collapsed rail (admin sidebar style)
- Built app inner nav (prompt **225**)
- New nav items or registry (prompt **226**)

## Acceptance criteria

- All platform groups collapsible on desktop and mobile drawer
- Active route's group auto-expands
- State persists across reload
- No regression to nav links, badges, or `navigationFromContract` fallback
- Frontend tests pass

## Manual test

1. Open `/launcher`; confirm only Workspace expanded by default
2. Expand Automations; reload; still expanded
3. Navigate to `/research`; Research group auto-expands
4. Collapse Workspace; Chat link hidden until re-expanded
