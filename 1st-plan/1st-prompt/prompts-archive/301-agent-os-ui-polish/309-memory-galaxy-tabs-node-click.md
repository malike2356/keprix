# Keprix Prompt 309: Memory Galaxy Brain tabs + node click

## Status: DONE

## Priority

Should, medium effort.

## Context

`/memory/galaxy` is a circle layout canvas without the Brain tabs strip used on `/memory`, and nodes do not open notes. Brain already has richer graph UX to reuse.

## Goal

1. Add the Brain/Memory tabs strip (or equivalent) on the galaxy page so Memory ↔ Galaxy navigation matches product IA.
2. Clicking a node opens the related vault note / memory document (existing vault or memory routes).
3. Keep circle layout for now; force layout is Prompt **313**.

## What already exists

- `frontend/src/app/(workspace)/memory/galaxy/page.tsx`
- `frontend/src/components/memory/MemoryGalaxyCanvas.tsx`
- Brain graph tabs / memory page patterns
- `GET /api/vault/graph`

## Tasks

1. Port or share the tabs strip from `/memory` (Galaxy active).
2. On node click: navigate or drawer-open note by path/id from graph payload.
3. Empty state: point to vault setup + capture, not only CLI.
4. Manual QA on sparse and dense graphs.

## Acceptance criteria

- [ ] Galaxy page shows Memory section tabs including Galaxy.
- [ ] Node click opens a note or shows a clear "no document" state.
- [ ] No regression on graph pan/zoom.
- [ ] Docs mention galaxy interactions.

## Dependencies

None hard. Nice follow-up **313**.

## Files likely touched

- `frontend/src/app/(workspace)/memory/galaxy/page.tsx`
- `frontend/src/components/memory/MemoryGalaxyCanvas.tsx`
- Possibly shared memory layout partial

## Related

- Build order: `prompts-archive/ref-301-agent-os-ui-polish-build-order.md`
