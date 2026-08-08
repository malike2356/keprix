# Prompt 467 / 00: Overview, gap inventory, architecture lock

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

**Depends on:** none
**Blocks:** 468+

## What was built

- Gap inventory locked: `docs/architecture/operator-gui-gap-inventory.md`
- Frozen route IA table (Tool ACL, Soft Wall safety, sheet/discovery, CRM, fleet,
  companion, data plane tabs, platform depth, catalog/sign-off)
- Soft Wall reuse policy, nav contract rules, feature-flag/edition gates
- Explicit non-goals and CRM sibling dependency (481)

## Why this exists

Codebase audit found many Keprix capabilities that exist as FastAPI routes,
libraries, or agent tools but lack (or mislabel) workspace GUI. Operators cannot
safely run ACL grants, data-plane imports, fleet, companion pairing, Soft Wall
safety ops, sheet enrich, or discovery jobs without curl. CRM programme 429-466
covers the agentic CRM console; this series closes **all other** identified GUI
gaps and gates CRM readiness.

## Goal

Lock the gap inventory, route IA, nav contract rules, Soft Wall reuse policy,
and Must vs Nice cut so later prompts do not invent parallel UIs.

## Must-haves

1. Publish gap inventory under `docs/architecture/operator-gui-gap-inventory.md`
   mirroring this series (Critical / High / Medium / Low / OK-agent-only).
2. Freeze route prefixes and ownership (see inventory Route IA table).
3. Nav rule: sync `navigation.py` and `navigation.ts` on every new route.
4. Soft Wall reuse: do not fork a second outreach approval inbox.
5. Tenant isolation on every new page.
6. Feature flags: document which surfaces need edition gates (fleet Enterprise).
7. Explicit non-goals: no nested Carina tree; no new Stripe prices; no Contabo
   marketing break; Telegram-only is not Must-done for operator safety surfaces.
8. Sibling CRM: this series **does not replace** 429-466. Prompt 481 fails if
   CRM Must GUI is missing.

## Acceptance

- [x] Gap inventory doc committed and matches prompt index
- [x] Route IA table frozen
- [x] Non-goals and CRM sibling dependency explicit

## Done When

468 can implement Tool ACL without re-debating IA.
