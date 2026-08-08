# Keprix Prompt 311: Action board header deep links

## Status: DONE

## Priority

Should, low effort.

## Context

Action Board at `/agent-os` already links to Run ledger in the header area. Glass, Onboarding, and Usage are easy to miss.

## Goal

Add header actions/links next to existing Run ledger control:

- Glass → `/agent-os/glass`
- Onboarding → `/agent-os/onboarding`
- Usage → `/usage`

## Tasks

1. Locate Action Board page header / toolbar.
2. Add text buttons or icon+label links (match existing Run ledger style).
3. Ensure mobile wrap does not hide primary Run actions.

## Acceptance criteria

- [ ] Three deep links visible on `/agent-os` board header.
- [ ] Style matches existing header actions.
- [ ] Works with Agent OS subnav from 301 (redundant is OK; discoverability first).

## Dependencies

After **301** preferred.

## Files likely touched

- `frontend/src/app/(workspace)/agent-os/page.tsx`
- Related Action Board components under `frontend/src/components/agent-os/`

## Related

- Build order: `prompts-archive/ref-301-agent-os-ui-polish-build-order.md`
