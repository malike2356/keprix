# Prompt 531 / CAS-15: Evals, pilot, cutover, rollback, sign-off, archive

**Status: COMPLETED 2026-08-08**
**Series:** 516-531
**Depends on:** 522-530
**Blocks:** none
**Writing style:** plain ASCII only.

## Goal

Prove Carina/Aiva consume Keprix capabilities in a capped pilot, then sign READY
or honest NOT READY, and archive completed prompts.

## Must-haves

1. Eval set: hallucination on empty tools, Soft Wall compliance, CRM enroll, booking
   offer, job cancel, fallback no-duplicate, entitlement deny, isolation.
2. Pilot plan: internal workspace, caps, observation window, rollback owner,
   kill procedure.
3. Progressive rollout: shadow -> opted primary -> default-on for non-admin tiers
   only after thresholds.
4. Sign-off doc: `docs/architecture/carina-aiva-keprix-sidecar-signoff.md` with
   shipped vs deferred (owner-gated Nice keys remain deferred).
5. Update gap map, self-knowledge, OPS runbooks, pending README.
6. Contabo: if deployed, verify `https://carinaai.uk/` = 200.
7. Archive CAS prompts only when READY; leave blocked items pending with status.
8. Writing-style scan on touched docs.

## Acceptance

- [ ] Pilot evidence attached (commands + results)
- [ ] Verdict READY or NOT READY with blockers listed
- [ ] Rollback drill recorded
- [ ] Completed prompts archived same session if READY

## Done When

Carina/Aiva full-Keprix-consumption programme is closed or explicitly paused.

## What was built

- Product sidecar `/v1/products/{carina|aiva}` with capability catalog
- Southbound Carina `/api/keprix/v1/*`, token exchange, Soft Wall, shadow, OPS probe
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py`
- Docs: gap map, security, sign-off, operator migration
