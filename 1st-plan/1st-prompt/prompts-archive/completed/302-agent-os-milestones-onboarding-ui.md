# Keprix Prompt 302: Day 1 / 7 / 30 milestones on onboarding

## Status: DONE

## Priority

High impact, low effort.

## Context

`GET /api/agent-os/milestones` and onboarding payload already embed day 1/7/30 progress. `/agent-os/onboarding` is a checklist UI that does not render milestones. Prompt 270 Task 4.5 claimed the wizard; the React surface is the gap.

## Goal

Render interactive Day 1 / Day 7 / Day 30 milestone cards on `/agent-os/onboarding` using the existing API (no new backend unless a tiny field is missing).

## What already exists

- `src/keprix/agent_os/milestones.py`
- `GET /api/agent-os/milestones`
- Onboarding route embeds milestones in some payloads (verify `GET /api/agent-os/onboarding`)
- `frontend/src/app/(workspace)/agent-os/onboarding/page.tsx`

## Tasks

1. Fetch milestones (dedicated endpoint or embedded onboarding JSON). Prefer one SWR key.
2. UI: three milestone cards (or a stepper) showing title, progress (`done` / `total`), current milestone highlight, and incomplete step list.
3. Link incomplete steps to existing onboarding step actions where IDs already map.
4. Empty / loading / error via shared `EmptyState` / skeletons / `ErrorState` (or Prompt 307 patterns).
5. Add a focused frontend or API contract test if useful; otherwise document manual check.

## Acceptance criteria

- [ ] `/agent-os/onboarding` shows Day 1, Day 7, Day 30.
- [ ] Progress numbers match API.
- [ ] Current milestone is visually marked.
- [ ] No CLI-only copy as the only path ("run keprix agent-os milestones").
- [ ] Works when Agent OS is enabled; graceful message when disabled.

## Dependencies

None hard. Better after 301 (subnav includes Onboarding).

## Files likely touched

- `frontend/src/app/(workspace)/agent-os/onboarding/page.tsx`
- Optional: `frontend/src/components/agent-os/MilestonesPanel.tsx`
- `docs/features/agent-os-phase4-workflows.md` (note UI path)

## Related

- Build order: `reference/301-agent-os-ui-polish-build-order.md`
