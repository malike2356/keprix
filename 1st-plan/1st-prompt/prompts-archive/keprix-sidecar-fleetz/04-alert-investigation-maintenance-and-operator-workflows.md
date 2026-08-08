# Prompt FZS-04: Fleetz alert, investigation, maintenance, and operator workflows

**Status: COMPLETED 2026-08-08**


## What was built

- `domain-packs/fleetz/` advisory sidecar (HTTP :3354, `/v1/products/fleetz/*`)
- Architecture, product API, streams/resilience, and pilot sign-off docs
- Deterministic calculators, safety gates, fixture connector, playbooks, simulator
- `keprix product provision|plan|status|rollback fleetz` CLI wiring
- Tests: `pytest domain-packs/fleetz/tests/test_fleetz_sidecar.py` (10 passed)
- Local deploy: `bash domain-packs/fleetz/scripts/deploy-local.sh`

**Depends on:** FZS-01, FZS-02
**Blocks:** FZS-05

## Goal

Deliver operator playbooks that reduce fuel loss and downtime without replacing
Fleetz detection rules or encouraging unsafe driver/device action.

## Must-haves

1. Fuel anomaly investigation correlates sensor quality, refuel/drain pattern,
   route, stop, ignition, geofence, driver assignment and historical baseline.
   Output is a case hypothesis and evidence, never an accusation of theft.
2. Alert triage groups duplicates, checks freshness, severity and dependencies,
   proposes next evidence and creates an approved case/task/notification.
3. Maintenance workflow turns mileage, engine hours, fault/health and schedule
   into a proposed task with parts, due window and evidence.
4. Daily fleet briefing covers offline vehicles, active alerts, fuel, utilisation,
   maintenance, overdue cases and data-quality gaps with clickable record ids.
5. Driver message uses neutral safety language, minimum location detail, configured
   language/channel and approval. Emergency guidance routes to human dispatch.
6. Route/geofence optimisation remains proposal and simulation. Product validates
   geometry, business rules and conflicts before any apply.
7. Web, mobile and Telegram operator prompts resolve linked identity/fleet and
   use product approval. No driver data is returned to unauthorised group chats.
8. Human takeover, audit, stop conditions, costs, retries and result reconciliation
   are defined for every playbook.

## Acceptance

- [ ] Fuel case clearly separates evidence from hypothesis
- [ ] Duplicate alert cannot cause duplicate outbound message
- [ ] Maintenance recommendation traces to deterministic data
- [ ] Emergency and vehicle control requests route to authorised humans
