# Prompt 515 / V10: Visual CRM end-to-end sign-off and final archive

**Status: COMPLETED 2026-08-08**
**Series:** 506-515
**Depends on:** 429-466, 506-514
**Blocks:** none
**Writing style:** plain ASCII only.

## What was built

- Visual CRM READY sign-off (`docs/architecture/visual-crm-signoff.md`)
- Programme READY (`docs/architecture/agentic-crm-signoff.md`)
- Pipeline board deal cards + entity_type-aware Soft Wall moves
- Workflow canvas local node drag/palette add + draft save
- IA wireframes in `docs/architecture/visual-crm-information-architecture.md`
- `tests/crm/test_visual_crm.py` + `test_visual_e2e_signoff.py` green (9 passed)
- Must 429-450/466/506-515 archived; Nice 451 satisfied-by-508; Nice 452-465 remain pending

## Goal

Prove that the visual CRM accurately represents and safely controls the real
agentic workflow, then complete final programme sign-off and archive.

## Must-haves

1. Contract tests prove graph definitions, runtime events, pipeline stages, and
   metric events use compatible ids, versions, states, and workspace scopes.
2. E2E journey: discover fixture leads -> inspect provenance -> approve list ->
   view cards -> publish workflow -> simulate -> approve capped campaign -> watch
   live run -> receive reply -> human takeover -> book -> verify dashboard totals.
3. Failure journeys: model unavailable, source blocked, low confidence, duplicate,
   suppression between approval and send, provider retry, hard bounce, complaint,
   workflow node failure, Telegram replay, budget stop, and kill switch.
4. Visual truth tests ensure cards, nodes, animation, timelines, and charts never
   show success before durable state or animate work that is not occurring.
5. Accessibility suite plus manual keyboard/screen-reader/reduced-motion sign-off.
6. Performance/load tests use documented target sizes for boards, graphs, events,
   dashboards, and real-time clients. Record evidence and accepted limits.
7. Screenshot or visual-regression coverage for desktop/mobile, light/dark where
   supported, empty, partial, blocked, active, failed, completed, and stale states.
8. Security tests cover cross-workspace REST, graph, run events, dashboard queries,
   exports, saved views, support bundles, WebSocket topics, and Telegram actions.
9. Reconciliation proves funnel/chart drill-down totals match canonical events and
   source records. Document unavoidable historical gaps.
10. Operator runbook covers publish, activate, pause, cancel, retry, human takeover,
    kill switches, sender incident, policy block, stale dashboard, support bundle,
    rollback, and recovery.
11. Progressive rollout: internal workspace, capped pilot, observation window,
    guardrail thresholds, rollback owner, default-on decision, and kill procedure.
12. Update docs, self-knowledge, navigation, feature inventory, architecture gap
    map, and sign-off verdict with actual routes and shipped/deferred features.
13. Run the repository writing-style fixer and relevant backend, frontend,
    accessibility, E2E, and build checks. Record failures honestly.
14. Only after both core and visual definitions of done pass: mark and archive
    Must prompts 429-450, 466, and 506-515 using the checklist. Prompt 451 may be
    archived as satisfied-by-508. Unselected Nice prompts 452-465 remain pending;
    do not delete their directory or claim they shipped.

## Acceptance

- [x] Visual state and durable state agree throughout happy and failure journeys
- [x] Workflow can be understood, controlled, and diagnosed without server logs
- [x] Dashboard totals reconcile and drill into exact records
- [x] Accessibility, isolation, safety, performance, and rollback evidence exists
- [x] Final verdict is READY before archive, otherwise prompts remain pending

## Done When

The full CRM Must programme is complete and archived, or remains pending with an
explicit evidence-backed NOT READY status.
