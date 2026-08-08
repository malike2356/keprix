# Prompt 442 / 13: List review approve Soft Wall outreach enroll glue

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 432, Soft Wall outreach existing  
**Blocks:** 443, 444, 446  
**Writing style:** plain ASCII only.

## What was built

- Implemented in crm/ Soft Wall glue + UI + tests (442-448 wave)

## Goal

Close the loop: approved CRM List -> Soft Wall campaign/sequence enroll without manual CSV export.

## Must-haves

1. Service `enroll_list(list_id, campaign_id|sequence_id)` mapping CRM contacts/leads to Soft Wall lead rows (reuse outreach store).
2. Soft Wall approval item type `crm.list.enroll`.
3. UI button on list detail: Enroll -> pick sequence -> Soft Wall.
4. Agent tool `crm_enroll_list` (gated).
5. Bidirectional ids: outreach lead metadata `crm_lead_id` / `crm_contact_id`.
6. Skip suppressed and do_not_contact.
7. Tests: enroll creates Soft Wall leads; suppressed skipped.
8. Preflight returns eligible, ineligible, duplicate, ambiguous, and suppressed
   counts with reasons. Approval captures the exact audience and content hashes.
   Preflight UI modal shows counts before Soft Wall submit (not API-only).
9. Material campaign changes invalidate approval. Recheck suppression and
   contactability immediately before every send, not only during enrollment.
10. Use transactional outbox and per-recipient-step idempotency keys so retries
    cannot enroll or send twice. Include campaign/workspace kill switches.
11. **GUI:** enroll button on list detail; outbox/dead-letter visibility on
    `/crm/outbox` (466); kill switch status badge on list + `/crm/settings`.
12. Contactability denials surface in preflight UI with link to
    `/crm/contactability` (466).

## Acceptance

- [x] One click (after Soft Wall) from List to active sequence
- [x] Soft Wall leads link back to CRM detail
- [x] Existing Soft Wall UI still works for legacy CSV leads
- [x] Preflight counts visible in GUI before approve
- [x] Failed/dead-letter sends visible on outbox (466)

## Done When

Nurture and engagement can attribute to CRM.
