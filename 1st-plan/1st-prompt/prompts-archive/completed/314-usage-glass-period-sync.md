# Keprix Prompt 314: Usage ↔ glass period query sync

## Status: DONE

## Priority

Nice, low effort.

## Context

After 305, glass has its own `days` control. Usage has a separate period toolbar. Operators comparing glass tokens vs `/usage` By agent get mismatched windows.

## Goal

Share the same query param convention (for example `?days=7` or usage's existing period keys) between `/agent-os/glass` and `/usage` so deep links and cross-navigation preserve the window.

## Tasks

1. Agree one param name (prefer aligning to usage's existing param if present; else `days`).
2. Glass and Usage read/write the same search params.
3. Cross-links (glass → usage By agent, usage → glass) preserve params.
4. Document the param in feature docs.

## Acceptance criteria

- [ ] Opening usage from glass keeps the selected period.
- [ ] Opening glass from usage keeps the selected period.
- [ ] Bookmarkable URLs.

## Dependencies

After **305**.

## Files likely touched

- Glass page, usage page, shared period helper
- `docs/features/agent-os-phase3-glass.md`

## Related

- Build order: `reference/301-agent-os-ui-polish-build-order.md`
