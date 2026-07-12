# Keprix Prompt 303: Phase 5 Ship defaults panel on glass

## Status: DONE

## Priority

High impact, medium effort.

## Context

Phase 5 backends exist (token playbook, guardrails, vault backup, error-paste) but are CLI/API only. Glass is the right product home for "ship defaults."

## Goal

Add a **Ship defaults** panel on `/agent-os/glass` that surfaces:

1. Token minimization playbook (list / expand techniques from `GET /api/agent-os/token-playbook`)
2. Guardrails status + **Backup vault** button (`GET/POST /api/agent-os/guardrails*`)
3. Error paste box (`POST /api/agent-os/error-paste`) showing classification + fix plan markdown

## What already exists

- `src/keprix/api/agent_os_phase5_routes.py`
- `src/keprix/agent_os/token_playbook.py`, `guardrails.py`, `workflows/error_paste.py`
- Glass page: `frontend/src/app/(workspace)/agent-os/glass/page.tsx`
- Docs: `docs/features/agent-os-phase5-polish.md`

## Tasks

1. Extend glass layout with a fifth region or a full-width Ship defaults section below the 2x2 grid.
2. Playbook: show technique count + titles; optional expand for summaries (do not dump entire markdown unless toggled).
3. Guardrails: show workspace root, approvals flag, vault_auto_backup; button triggers backup and shows path/size toast or inline result.
4. Error paste: textarea + submit; render `output` markdown and classification chip; clear CTA to paste again.
5. Handle 403 when Agent OS disabled.
6. Update phase5 docs to list the UI path.

## Acceptance criteria

- [ ] Glass shows playbook, guardrails, error-paste without leaving the page.
- [ ] Backup vault succeeds against a configured vault in dev.
- [ ] Error paste classifies `ModuleNotFoundError` and shows a plan.
- [ ] No new design system; use Paper / Stack / existing chips.
- [ ] Docs updated.

## Dependencies

Prefer after **301** (glass as hub home). APIs already shipped.

## Files likely touched

- `frontend/src/app/(workspace)/agent-os/glass/page.tsx`
- `frontend/src/components/agent-os/ShipDefaultsPanel.tsx` (new)
- `docs/features/agent-os-phase5-polish.md`
- `docs/features/agent-os-phase3-glass.md`

## Related

- Build order: `reference/301-agent-os-ui-polish-build-order.md`
