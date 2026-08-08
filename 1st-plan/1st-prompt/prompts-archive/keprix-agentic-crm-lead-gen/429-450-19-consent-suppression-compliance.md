# Prompt 448 / 19: Consent, suppression, PECR and GDPR controls

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 430, 442  
**Blocks:** 450  
**Writing style:** plain ASCII only.

## What was built

- Implemented in crm/ Soft Wall glue + UI + tests (442-448 wave)

## Goal

Make lawful outreach a product feature, not a footnote.

## Must-haves

1. ConsentRecord: basis (legitimate_interest, soft_opt_in, contract, consent), evidence, captured_at, source.
2. SuppressionEntry: email/phone/telegram, reason, permanent flag.
3. Send path checks suppression + consent policy before Soft Wall send.
4. Unsubscribe link / reply keyword handling.
5. UI: consent editor on contact detail; suppression manager at
   `/crm/suppressions`; contactability decisions at `/crm/contactability` (466).
6. Workspace policy defaults for UK (document as defaults, not legal advice);
   editable under `/crm/settings` with Soft Wall.
7. Audit events for consent changes (visible on contact timeline).
8. Tests: suppressed contact never enrolled/sent.
9. Policy decision records include person/entity, purpose, channel, jurisdiction,
   policy version, evidence, expiry, and explanation. Discovery is not consent.
10. Suppression wins at import, materialisation, enrollment, scheduling, send,
    reply drafting, and channel handoff. Test the approval-to-send race window.
11. Implement subject access export, correction, erasure, retention expiry, and
    permanent minimal suppression retention with auditable runbooks; export
    triggerable from contact detail Soft Wall.
12. Prohibit special-category inference, minors, vulnerable-person targeting,
    discriminatory filters, and health/care-recipient lead generation.
13. Sender readiness / deliverability checklist UI on `/crm/deliverability` (466)
    is a hard gate before first cold campaign Soft Wall.

## Acceptance

- [x] Enroll refuses suppressed
- [x] Unsubscribe from reply works
- [x] Docs: `docs/features/crm-compliance.md`
- [x] Operator can manage suppressions and contactability from GUI
- [x] Sender readiness visible before enroll of cold lists

## Done When

Cold outreach cannot ignore suppression by accident.
