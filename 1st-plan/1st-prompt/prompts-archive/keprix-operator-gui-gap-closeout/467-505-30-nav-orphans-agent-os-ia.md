# Prompt 497 / 30: Nav orphans + Agent OS IA findability (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- document-agents nav; Agent OS more links include self-improvement + improvements
- Commerce group populated (billing, upgrade)


**Depends on:** 467
**Blocks:** 505

## Goal

Pages exist but are hard to find: document-agents, Agent OS audit/runs/promote /
skill-review, self-improvement settings, privacy, sdk, launcher, etc.

## Must-haves

1. Audit orphan workspace pages vs nav and Hub. Minimum Must link targets:
   - `/document-agents`
   - Agent OS: `/agent-os` glass index linking audit, runs, promote,
     skill-review, skill-proposals, connections, loop-profiles, maturity,
     onboard/onboarding, improvements (488)
   - `/settings/agent/self-improvement`
   - `/privacy` (if operator-facing)
   - `/developer` / module inventory (already present; ensure linked)
2. Prefer Hub cards or Agent OS index over flooding the primary sidebar.
3. Commerce nav group: either populate with billing/upgrade entries or remove
   empty group (do not leave a dead group).
4. Sync `navigation.py` + `navigation.ts`; every href must resolve to a page.
5. Feature flags / roles respected (FLAG_NAV_GATES).
6. Frontend smoke for newly linked routes.
7. Docs sitemap / operator GUI map updated in 502.
8. Do not delete orphan pages; make them findable or mark intentional deep-link
   only in 504 register with owner note.

## Acceptance

- [x] Document agents reachable without memorising URL
- [x] Agent OS subpages linked from glass/index
- [x] Self-improvement linked from Agent settings
- [x] Empty commerce group resolved
- [x] Zero nav hrefs to missing pages

## Done When

Shipped pages are discoverable.
