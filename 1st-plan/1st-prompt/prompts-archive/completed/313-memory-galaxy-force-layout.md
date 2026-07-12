# Keprix Prompt 313: Force-directed Memory Galaxy layout

## Status: DONE

## Priority

Nice, medium effort.

## Context

Galaxy uses a circle layout. Brain already ships force / temporal / radial / hierarchical layouts in `frontend/src/lib/brain/layout-registry.ts`.

## Goal

Offer a force-directed layout mode on Memory Galaxy by reusing Brain layout patterns (worker-friendly for 100+ nodes). Keep circle as default or selectable.

## Tasks

1. Reuse Brain force layout registry rather than rewriting physics.
2. Add layout toggle on galaxy page (Circle | Force).
3. Persist preference in URL or localStorage.
4. Performance: do not block UI on large graphs; mirror Brain incremental strategy where practical.

## Acceptance criteria

- [ ] User can switch to force layout.
- [ ] Layout reuses Brain code paths (no duplicate force engine).
- [ ] Node click from 309 still works.
- [ ] Documented in memory/galaxy feature docs.

## Dependencies

After **309** (interactions first).

## Files likely touched

- `frontend/src/components/memory/MemoryGalaxyCanvas.tsx`
- `frontend/src/lib/brain/layout-registry.ts` (reuse)
- Galaxy page controls

## Related

- Build order: `reference/301-agent-os-ui-polish-build-order.md`
- Brain layout: completed prompt 257
