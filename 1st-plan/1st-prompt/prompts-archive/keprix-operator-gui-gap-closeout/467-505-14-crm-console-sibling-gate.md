# Prompt 481 / 14: CRM operator console sibling gate (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- Verified all 466 Must `/crm/*` routes exist
- Soft Wall safety CRM pages wired to outreach implementations (no stubs)
- Inbox + workflows Must-thin Soft Wall glue (approvals/replies/sequences)
- Gap map updated: operator console SHIPPED / READY for 481
- Tests: `tests/frontend/test_discovery_crm_gate.py`


**Depends on:** sibling series 429-450 + 466 (and ideally 475-480)
**Blocks:** 505

## Why this exists

Critical CRM GUI gaps are owned by `keprix-agentic-crm-lead-gen` (especially
466). This series must not claim CRM closed without that pack. This prompt is
the **execution/verification gate**, not a second CRM implementation.

## Goal

Execute or verify CRM Must GUI IA from prompt 466 and gap map; close any residual
holes (accounts/deals/inbox/workflows Must-thin) without forking architecture.

## Must-haves

1. Confirm `/crm` routes from 466 IA exist and pass smoke tests.
2. If CRM series not yet built: **build CRM per 429-466 prompts in order** as
   part of this gate (do not invent a thinner parallel CRM).
3. Wire Soft Wall safety pages (469-474) as CRM deep links / shared components.
4. Wire sheet/discovery (477-480) into CRM nav.
5. Product `/leads` vs Soft Wall vs CRM leads labeled (see 498).
6. Update `docs/architecture/agentic-crm-gap-map.md` status.
7. Sign partial evidence into 503 checklist.

## Acceptance

- [x] Operator can discover -> Soft Wall list -> enroll -> inbox without curl
- [x] All 466 Must routes present or explicitly owner-deferred with NOT READY
- [x] No duplicate CRM object model

## Done When

CRM Critical gap is closed or owner-blocked in sign-off (never silent).
