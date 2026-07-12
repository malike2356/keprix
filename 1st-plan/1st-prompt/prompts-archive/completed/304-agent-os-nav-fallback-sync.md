# Keprix Prompt 304: Sync frontend nav fallback with NAV_ITEMS

## Status: DONE

## Priority

High impact, low effort.

## Context

Live nav usually comes from `GET /api/ui/contract`. Frontend `primaryNavigation` fallback can omit `agent-os-glass` and `memory-galaxy`, so contract-down or offline builds silently drop links. Icon id `dashboard` may fall back to a generic grid.

## Goal

Keep `frontend/src/lib/navigation.ts` (and launcher lists if separate) aligned with `src/keprix/ui_contract/navigation.py` for Agent OS glass + Memory Galaxy. Map missing icons.

## Tasks

1. Diff backend `NAV_ITEMS` vs frontend fallback; add missing glass + galaxy entries with same ids/hrefs/groups.
2. Ensure `nav-icons.ts` (or equivalent) maps `dashboard` (and any other Agent OS icons) to a real icon.
3. After Prompt 301 nav collapse, update both backend and fallback in the same PR so they stay twins.
4. Add a small unit test or script assertion that critical ids exist in both lists (optional but preferred).

## Acceptance criteria

- [ ] Fallback includes glass (`/agent-os/glass`) and galaxy (`/memory/galaxy`).
- [ ] Ids match backend (`agent-os-glass`, `memory-galaxy`).
- [ ] No broken icon ids for those entries.
- [ ] Document that contract is source of truth; fallback is mirror.

## Dependencies

Coordinate with **301** (hub collapse). Can ship in the same PR as 301.

## Files likely touched

- `frontend/src/lib/navigation.ts`
- `frontend/src/components/shell/nav-icons.ts` (or similar)
- `src/keprix/ui_contract/navigation.py` (if 301 changes labels/hrefs)
- Optional test under `frontend` or `tests/`

## Related

- Build order: `reference/301-agent-os-ui-polish-build-order.md`
