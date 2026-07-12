# Keprix Prompt 305: Glass period selector

## Status: DONE

## Priority

High impact, low effort.

## Context

Glass API accepts `days` (1-90) but the UI hardcodes `days=7`. Usage page already has a period toolbar/chart pattern.

## Goal

Add a period control on `/agent-os/glass` that sets `days` and refetches glass + token breakdown. Reuse usage period UI patterns (do not invent a third control).

## What already exists

- `GET /api/agent-os/glass?days=`
- Usage period toolbar / `UsageModelBreakdownChart` on `/usage`
- Glass page SWR fetch

## Tasks

1. Extract or reuse a period control component from usage (or shared `components/usage/`).
2. Wire glass SWR key to include `days` (URL query `?days=` preferred for shareability; pairs with 314).
3. Default 7; allow 1, 7, 30, 90 (match API limits).
4. Show selected period on the tokens panel header.

## Acceptance criteria

- [ ] Changing period refetches glass data.
- [ ] Invalid days coerced or rejected per API.
- [ ] Control matches usage look-and-feel enough to feel finished.
- [ ] No hardcoded `days=7` left as the only path.

## Dependencies

None. **314** extends this with usage sync.

## Files likely touched

- `frontend/src/app/(workspace)/agent-os/glass/page.tsx`
- Possibly `frontend/src/components/usage/*`

## Related

- Build order: `reference/301-agent-os-ui-polish-build-order.md`
