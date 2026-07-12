# Keprix Prompt 310: Glass Tasks links + workflow boards

## Status: DONE

## Priority

Should, low effort.

## Context

Glass Tasks panel "Open" uses a vague board link (`links.board` → `/agent-os`) while payload also has tasks link and `workflow_boards`. Operators cannot jump to `/tasks` or a specific workflow board.

## Goal

- Primary CTA: open `/tasks` (or `links.tasks` when present).
- Secondary: list workflow boards from glass payload with links into kanban/workflow board UI already used by Agent OS.

## Tasks

1. Read glass payload fields (`tasks`, `links`, `workflow_boards`).
2. Fix primary Open button href.
3. Render workflow board rows (title, workflow id) with working hrefs.
4. Empty state when no boards.

## Acceptance criteria

- [ ] Tasks CTA lands on the real tasks surface.
- [ ] At least one workflow board from a content-series run is openable after Phase 2 usage.
- [ ] No dead `/agent-os` loop presented as "tasks".

## Dependencies

Optional after **303** (layout space). Can ship independently on glass page.

## Files likely touched

- `frontend/src/app/(workspace)/agent-os/glass/page.tsx`
- `src/keprix/agent_os/glass_dashboard.py` only if link fields are wrong

## Related

- Build order: `reference/301-agent-os-ui-polish-build-order.md`
