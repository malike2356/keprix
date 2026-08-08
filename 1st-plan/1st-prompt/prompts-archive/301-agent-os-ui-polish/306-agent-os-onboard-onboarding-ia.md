# Keprix Prompt 306: Unify onboard vs onboarding IA

## Status: DONE

## Priority

High impact, low effort.

## Context

Two routes confuse operators:

- `/agent-os/onboard` : interview / connections-style flow (Nate Herk pack)
- `/agent-os/onboarding` : activation checklist + (after 302) milestones

Onboard lacks `PageHeader`/breadcrumbs polish.

## Goal

Make the twin routes unmistakable via clear titles, PageHeader, breadcrumbs, and optional tabs linking each other. Do not merge the backends.

## Tasks

1. On `/agent-os/onboard`: add `PageHeader` titled **Onboard interview** (or product copy), short subtitle, breadcrumb Agent OS → Onboard.
2. On `/agent-os/onboarding`: header **Activation checklist** (or **Day 1 / 7 / 30**), link to interview.
3. Optional: shared tabs `Interview | Checklist` on both pages.
4. Subnav (301) should point Onboarding to the checklist; put interview under checklist "More" or second tab.
5. Update nav labels in backend + fallback so they are not both "Agent OS onboard*".

## Acceptance criteria

- [ ] A new user can tell interview vs checklist in under 3 seconds.
- [ ] Both pages use PageHeader + consistent breadcrumbs (see 308).
- [ ] Cross-links exist both ways.
- [ ] Nav labels are distinct.

## Dependencies

After **301**. Milestones (**302**) live on checklist page.

## Files likely touched

- `frontend/src/app/(workspace)/agent-os/onboard/page.tsx`
- `frontend/src/app/(workspace)/agent-os/onboarding/page.tsx`
- `src/keprix/ui_contract/navigation.py`
- `frontend/src/lib/navigation.ts`

## Related

- Build order: `prompts-archive/ref-301-agent-os-ui-polish-build-order.md`
