# Agentic CRM self-knowledge outline

**Status:** SNIPPETS SHIPPED (prompt 449)  
**Date:** 2026-08-08  
**Architecture:** `docs/architecture/agentic-crm-gap-map.md`  
**Feature doc:** `docs/features/agentic-crm.md`

## Programme

Keprix agentic CRM + lead-gen funnel (prompts 429-450 + 466). Domain-agnostic
spreadsheet preprocess, CRM objects, discovery packs, Soft Wall enroll,
nurture stages, engagement ingest, viCal handoff, Telegram + workspace GUI.

## Packages

- `src/keprix/crm/`
- `src/keprix/sheet_preprocess/`
- `src/keprix/discovery/`
- Soft Wall: `src/keprix/outreach/` (glue, do not fork)
- Booking: `src/keprix/vical/`

## Object names (frozen)

Account, Lead, Contact, Deal, Activity, List, EnrichmentJob, ConsentRecord
(plus ListMembership, SuppressionEntry, and operator types in the gap map).

## Stage machine (frozen)

discovered -> enriched -> listed -> approved -> enrolled -> contacted ->
engaged -> qualified -> booked -> customer -> paying  
(also: suppressed, bounced, do_not_contact, lost)

## Soft Wall gates (summary)

Discovery list before enrich; enrich before write; list before enroll; first
outbound; stage jump to customer/paying; external scrape; identity merge;
kill-switch off; contactability allow when needs_review.

## Must GUI

All Soft Wall-gated capabilities under `/crm/*` (see gap map IA table and
prompt 466). Telegram-only is not Must-done.

## Parity snippets (449)

- `agentic-crm-objects.md`
- `agentic-crm-routes.md`
- `agentic-crm-tools.md` (includes crm enroll / crm_enroll_list)
- `agentic-crm-packs.md`
- `agentic-crm-compliance.md`
- Feature runbook: `docs/features/agentic-crm.md`
- Pack docs: `docs/features/crm-packs/{generic,property,health_social}.md`

Index smoke: after self-knowledge ingest, `keprix memory search-self "crm enroll"`
should retrieve tools/routes chunks.

## Non-goals (one-liners for retrieval)

No Carina nest. No silent illegal scrape. No new Stripe prices. No parallel
approval system beside Soft Wall. Discovery is not contact permission.
