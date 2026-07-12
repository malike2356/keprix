# Keprix Prompt 307: Shared EmptyState / ErrorState / skeletons on Agent OS pages

## Status: DONE

## Priority

Should (polish consistency), medium effort.

## Context

Glass, galaxy, maturity, and connections often use raw Paper/Typography without shared loading/empty/error primitives. Design system already ships them under `frontend/src/components/ui/`.

## Goal

Adopt `PageHeader`, `EmptyState`, `ErrorState`, and skeleton/`AsyncView` patterns on:

- `/agent-os/glass`
- `/memory/galaxy`
- `/agent-os/maturity`
- `/agent-os/connections`

(and onboard/onboarding if still raw after 306)

## Tasks

1. Inventory each page's loading / empty / error branches.
2. Replace ad-hoc text with shared components.
3. Keep existing data hooks; do not rewrite fetch layer unless needed.
4. Ensure glass shows skeletons while SWR loads; galaxy empty state is product copy, not only CLI hints.

## Acceptance criteria

- [ ] Listed pages use shared empty/error/loading components.
- [ ] Failed fetch does not blank the whole shell.
- [ ] Visual consistency with `/usage` and `/memory` pages.

## Dependencies

Can run parallel to 301-306. Avoid conflicting with 303 glass panel edits (coordinate or land after 303).

## Files likely touched

- Listed page.tsx files
- `frontend/src/components/ui/*` (consume only)

## Related

- Build order: `reference/301-agent-os-ui-polish-build-order.md`
