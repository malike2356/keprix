# Prompt 450 / 21: Core tests, cutover, and visual sign-off handoff

**Status: COMPLETED 2026-08-08** (pending parent archive; do not leave orphan)

## What was built

- `docs/architecture/agentic-crm-signoff.md` Verdict READY (core); 515 owns final archive
- pytest evidence: 78 passed (crm + discovery + sheet_preprocess + frontend smoke)
- Optional `scripts/e2e-crm-funnel.sh` with GUI path notes
- Gap map + GUI Soft Wall checklist recorded; Contabo not required

**Series:** 429-450  
**Depends on:** all prior Must including 466  
**Blocks:** 506-515  
**Writing style:** plain ASCII only.

## Goal

Prove the funnel core, cut over guarded routes, prove baseline GUI surfacing,
and hand stable contracts to visual prompts 506-515. Final READY and Must archive
belong to prompt 515.

## Must-haves

1. pytest packs: `tests/crm/`, `tests/sheet_preprocess/`, `tests/discovery/` (min coverage for Must paths).
2. Frontend smoke tests for **all** Must `/crm` routes in 466 IA table (pattern
   like calendar views tests). Missing route = NOT READY.
3. E2E script optional: `scripts/e2e-crm-funnel.sh` (CH mock -> list -> Soft Wall enroll -> classify fixture) with GUI path notes.
4. Feature flag `KEPRIX_CRM_FUNNEL=1` default on for multi-user workspaces when ready; document kill switch; GUI hides CRM nav when off.
5. Sign-off doc `docs/architecture/agentic-crm-signoff.md` with Verdict READY/NOT READY.
6. Record core READY/NOT READY but do not archive the CRM Must series until
   prompt 515 validates the visual workflow, pipeline, runtime, and dashboards.
7. Verify carinaai.uk / keprixai.com unaffected (no Contabo CRM deploy required for sign-off unless owner asks).
8. Execute every final sign-off check in `ref-429-programme-hardening-review.md`,
   including tenant isolation, sender readiness, idempotency, suppression races,
   reply pause, kill switches, degraded non-AI paths, and retention workflows.
9. Use a capped non-production pilot before default-on rollout. Record rollback
   criteria, owner, observation window, complaint ceiling, and stop procedure.
10. **GUI surfacing gate:** each Must capability has a documented operator path
    (route or Soft Wall panel). Telegram-only or API-only fails Must sign-off.
    Checklist mirrors 466 Acceptance.

## Acceptance

- [ ] Test suites green in CI or documented local evidence
- [ ] Sign-off filled including 466 GUI checklist
- [ ] Visual sprint receives stable API, event, permission, and metric contracts
- [ ] Operator can complete discover -> list -> enroll -> reply inbox without curl

## Done When

Core is ready for prompts 506-515 or explicitly blocked with evidence. Do not
archive partial work; prompt 515 owns final Must archival.
