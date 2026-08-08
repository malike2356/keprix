# Prompt 473 / 06: Identity merge suggestions Soft Wall GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

**Depends on:** 467

## What was built

- Soft Wall safety GUI wave: `/outreach/deliverability`, `/outreach/outbox`, `/outreach/suppressions`, `/outreach/contactability`, `/outreach/merges`, `/outreach/settings`
- CRM API extensions: deliverability rates/block, outbox retry/cancel, suppressions undo/bulk, merge reject
- Client helpers in `frontend/src/lib/crm-api.ts`; tabs in `OutreachTabNav`
- Docs: `docs/features/soft-wall-safety.md`
- Tests: `tests/frontend/test_soft_wall_safety_gui.py`

**Blocks:** 505
**Aligns with:** CRM 430/466

## Goal

Fuzzy identity matches must produce Soft Wall merge suggestions with provenance
diff. Never silent merge; never merge consent across people.

## Must-haves

1. Route `/outreach/merges` (+ `/crm/merges`).
2. List suggested merges: confidence, matching keys, field provenance side-by-side.
3. Soft Wall approve/reject; reversible soft-merge window documented.
4. Consent/suppression never auto-union across distinct people without explicit
   Soft Wall step labeled "consent transfer" (default deny).
5. Agent tool may propose; GUI is source of truth for apply.
6. Tests: fuzzy suggest only; exact verified key merge path tested separately.
7. Nav entry.

## Acceptance

- [x] Operator reviews provenance diff before merge
- [x] Reject leaves both records
- [x] Consent cannot silently combine

## Done When

Dedupe is human-gated in GUI.
