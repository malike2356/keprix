# Agent brief: Prompt 118 admin dashboard verification

**Status:** Archived in `prompts-archive/118-admin-dashboard-with-flexy.md`  
**Reconciled:** 2026-07-05 (all acceptance items confirmed)  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/frontend/src/app/(admin)/`  
**Goal:** Confirm Flexy-style admin shell meets acceptance criteria; fix gaps only.

## Context

Prompt 118 is archived. Sidebar, overview, Tabler icons, and conversation table are
implemented. This brief is a verification pass against the original acceptance
criteria.

## Already done (do not redo)

- Flexy-style sidebar with 9 nav items (`components/admin/admin-nav.ts`)
- Tabler icons on dashboard pages and sidebar
- Overview: stat cards, ApexCharts, SWR data hooks
- Wired pages: tools, mutations, memory, channels, keys, users, settings, conversations
- `AdminHeader` with bell and profile menu
- Split auth layout on `/auth/login` and `/auth/setup`

## Remaining gaps to verify or fix

| Item | Path | Action |
| --- | --- | --- |
| Setup wizard 4 steps | `src/app/auth/setup/page.tsx` | Confirm Welcome, Owner, LLM provider, Done; POST to `/api/setup/step/{n}` |
| Setup gate | backend | Confirm setup route blocked when `KEPRIX_SETUP_COMPLETE=true` |
| Channel health data | `dashboard/channels/page.tsx` | Confirm uses `GET /api/channels/overview` (not hardcoded mock) |
| Loading skeletons | `dashboard/page.tsx` | SWR loading states on charts and tables |
| localStorage sidebar | `components/admin/Sidebar.tsx` | Collapse state persists across refresh |
| Brand strings | `frontend/src` | `rg -i 'saasable|flexy' src/app/\(admin\) src/components/admin` must be empty |

## Verification commands

```bash
cd /opt/lampp/htdocs/verlox/keprix
.venv/bin/python -m pytest tests/api/test_admin_workspace.py -q

cd frontend
pnpm build
```

Manual checks:

1. Log in as admin; open `/dashboard`
2. Toggle sidebar collapse; refresh; state should persist
3. Open Conversations; table loads from API; delete and open-in-chat work
4. Run setup wizard on a fresh instance (`KEPRIX_SETUP_COMPLETE=false`)

## Acceptance checklist

- [x] Sidebar: 9 items, correct icons, collapse to icon-only
- [x] Header: notification bell, profile dropdown
- [x] Dashboard: 4 stat cards, 2 charts, 1 table, 1 timeline; API-backed with loading states
- [x] Login: split layout, KeprixLogo left, form right
- [x] Setup: 4 steps advance on submit via `/api/setup/step/{n}`
- [x] `pnpm build` passes
- [x] No SaasAble or Flexy branding strings in UI copy

## Out of scope

- Prompt 137 admin workspace API extensions (already archived)
- Marketing landing (Prompt 117)
- Wiring `keprix/keprix/backend/` teams or browser modules (Prompts 52-56)
