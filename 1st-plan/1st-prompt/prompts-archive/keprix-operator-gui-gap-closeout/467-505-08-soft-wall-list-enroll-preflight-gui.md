# Prompt 475 / 08: Soft Wall list enroll + preflight GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- Preflight + enroll APIs: `POST /api/outreach/lists/{id}/enroll-preflight` and `/enroll`
- GUI Soft Wall enroll modal on `/outreach/lists` with counts and fix links
- Audience hash Soft Wall gate; suppressed/contactability-deny skip; outbox enroll rows
- Tests: `tests/frontend/test_soft_wall_enroll_vical.py`
- Docs: `docs/features/soft-wall-enroll-vical.md`


**Depends on:** 470, 471, 472, 474
**Blocks:** 505
**Aligns with:** CRM 442

## Goal

Close list -> Soft Wall sequence enroll with preflight counts in GUI (eligible,
ineligible, duplicate, ambiguous, suppressed). Works for Soft Wall lists now;
CRM lists when 442/466 land.

## Must-haves

1. Enroll CTA on Soft Wall list/campaign pages and CRM list detail when present.
2. Preflight modal: counts + reasons; Soft Wall approval captures audience hash.
3. Skip suppressed and contactability-deny; show links to fix.
4. Bidirectional ids: Soft Wall lead metadata `crm_lead_id` when CRM exists.
5. Outbox integration after enroll (470).
6. Agent tool gated; returns deep links.
7. Tests for enroll + suppressed skip + Soft Wall gate.
8. Material campaign change invalidates prior approval (UI message).

## Acceptance

- [x] One Soft Wall-gated click from list to sequence
- [x] Preflight visible before approve
- [x] Legacy Soft Wall CSV leads still work

## Done When

Enroll is not a CSV export dance.
