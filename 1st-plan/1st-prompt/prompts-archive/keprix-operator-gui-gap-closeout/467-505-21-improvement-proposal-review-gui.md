# Prompt 488 / 21: Auto-improvement proposal review GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/agent-os/improvements` Soft Wall apply/reject/defer
- reject/apply/defer API routes; settings deep-link; docs/features/improvement-loop.md


**Depends on:** 467, `/api/improvement`, Agent OS self-improvement settings
**Blocks:** 505

## Goal

Settings toggle exists; proposal approve/metrics API needs a review UI.

## Must-haves

1. Route `/agent-os/improvements` (prefer dedicated page; if extending
   `/agent-os/skill-proposals`, retitle and section so improvement API proposals
   are not confused with Agent OS skill proposals).
2. List proposals from `/api/improvement`: type (prompt/tool-gap/skill/pattern),
   status, created_at, risk, diff summary, predicted metrics.
3. Detail: full diff, related session/run ids, Soft Wall Approve / Reject /
   Apply / Defer.
4. Default Soft Wall on apply even when auto_apply settings exist; settings page
   links here and explains Soft Wall still wins for production workspaces.
5. Metrics panel: accepted vs rejected, rollback count, last apply actor.
6. Empty state: no proposals; link to enable detection in self-improvement settings.
7. Nav under Automations / Agent OS; sync contracts; Hub card optional.
8. Workspace isolation; never show raw secrets from proposal payloads.
9. Tests: list/detail Soft Wall apply; reject leaves runtime unchanged.
10. Docs: Agent OS improvement loop operator section.

## Acceptance

- [x] Operator reviews and Soft Wall-applies a proposal from GUI
- [x] Reject leaves runtime unchanged
- [x] Self-improvement settings deep-links to this review UI
- [x] Non-admin cannot apply

## Done When

Improvement loop is human-gated in GUI.
