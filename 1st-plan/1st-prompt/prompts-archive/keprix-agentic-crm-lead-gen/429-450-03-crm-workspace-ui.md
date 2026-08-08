# Prompt 432 / 03: CRM workspace UI (lists, detail, CRUD)

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 431  
**Blocks:** 437, 442, 466  
**Writing style:** plain ASCII only.

## What was built

- CRM workspace UI under frontend /crm/* with Soft Wall panel
- Nav synced (crm_funnel flag)
- List PATCH/DELETE API enablement


## Goal

Operator-facing CRM in the workspace nav for review and CRUD. API-only is not
enough; every object in 430 must be reachable from GUI.

## Must-haves

1. Nav item under Workspace (sync `navigation.py` + `frontend/src/lib/navigation.ts`).
2. Pages (foundation; 466 extends operator console):
   - `/crm` overview (funnel KPIs stub + Soft Wall CRM pending)
   - `/crm/lists`, `/crm/lists/[id]`
   - `/crm/leads`, `/crm/leads/[id]`
   - `/crm/contacts`, `/crm/contacts/[id]`
   - `/crm/accounts`, `/crm/accounts/[id]`
   - `/crm/deals`, `/crm/deals/[id]`
3. List tables: stage chips, source, company, email, last touch, Soft Wall status.
4. Detail: fields edit, activity timeline, enroll CTA, Soft Wall campaign link,
   viCal link when present, field provenance badges (source + confidence).
5. Bulk select: approve, suppress, delete, enroll.
6. Empty states honest (no fake demo companies).
7. Reuse Soft Wall UI patterns; migrate or deep-link legacy `/leads`.
8. Soft Wall panel on `/crm` for CRM-related approvals (create/update/delete).
9. Leave stubs/nav links for routes owned by later Musts (jobs, inbox,
   deliverability, outbox, merges, contactability, workflows, settings) so 466
   can fill without renumbering IA.

## Acceptance

- [x] Operator can CRUD account, lead, contact, deal, list membership without API tools
- [x] Soft Wall pending items visible from `/crm` and list detail
- [x] Mobile-usable tables
- [x] Provenance visible on detail (not hidden in JSON only)

## Done When

Discovery and enroll glue have a human review surface; 466 can extend nav.
