# Keprix Prompt 301: Agent OS hub + subnav

## Status: DONE

## Priority

High impact, medium effort. First in series 301-315.

## Context

Automations currently lists ~12 flat Agent OS entries (glass, board, audit, onboard, onboarding, maturity, connections, skills, promote, runs, loops, client kit). Users miss Glass and Galaxy. Backends already exist.

## Goal

Make `/agent-os` (or `/agent-os/glass`) a hub with an in-content subnav: **Glass | Board | Onboarding | Memory | Usage**. Collapse or nest secondary items under the hub so discoverability improves without new APIs.

## What already exists

- Routes under `frontend/src/app/(workspace)/agent-os/`
- Backend `NAV_ITEMS` in `src/keprix/ui_contract/navigation.py` (`agent-os-board`, `agent-os-glass`, ...)
- Frontend fallback `frontend/src/lib/navigation.ts`
- Shared `PageHeader`

## Tasks

1. Add `AgentOsSubnav` (or layout) under `frontend/src/components/agent-os/` with links:
   - Glass → `/agent-os/glass`
   - Board → `/agent-os`
   - Onboarding → `/agent-os/onboarding`
   - Memory → `/memory/galaxy` (or `/memory`)
   - Usage → `/usage`
2. Mount subnav from a shared `agent-os` layout or on each primary page via composition (prefer one layout route group if Next App Router allows without breaking existing paths).
3. Reduce Automations primary nav noise:
   - Keep one top-level **Agent OS** entry pointing at glass (or hub).
   - Move audit / maturity / connections / skill-* / promote / runs / loop-profiles to secondary links on the hub or a "More" section inside Agent OS, not 12 siblings.
4. Update backend `NAV_ITEMS` and frontend fallback together (pair with Prompt 304).
5. Document the hub in `docs/features/agent-os-overview.md`.

## Design rules

- Reuse MUI + existing tokens; no new design system.
- Subnav is tabs or a simple horizontal link row, not a second sidebar.
- Active state must match current pathname.

## Acceptance criteria

- [ ] Primary pages show the five-item subnav.
- [ ] Automations sidebar no longer lists all Agent OS routes as flat equals.
- [ ] Glass is reachable in one click from Automations.
- [ ] No broken hrefs; mobile layout does not overflow.
- [ ] Docs mention the hub.

## Dependencies

None (start of series). Unlocks 303, 306, 308, 311.

## Files likely touched

- `frontend/src/app/(workspace)/agent-os/**`
- `frontend/src/components/agent-os/*`
- `src/keprix/ui_contract/navigation.py`
- `frontend/src/lib/navigation.ts`
- `docs/features/agent-os-overview.md`

## Related

- Build order: `reference/301-agent-os-ui-polish-build-order.md`
- Master: `reference/301-agent-os-ui-polish-master-reference.md`
