# Prompt 464 / N14: Property portal adapters (flagged production path)

**Status: COMPLETED 2026-08-08**
**Series:** 429-465
**Depends on:** 440 (pack + legal checklist), 436, 448
**Blocks:** none
**Writing style:** plain ASCII only.

## What was built

- Soft Wall checklist ack + kill switch + portal gate status
- Workspace Connections flag `property_portal_adapters_enabled` and Rightmove/Zoopla feed tokens
- CSV property path remains always-on without portals
- Docs: Connections + existing property portal legal checklist
- Tests: flag enable via Connections in `tests/crm/test_connections.py`
- Operator step remaining: acknowledge checklist, enable flag, enter licensed feed tokens if contracted

## Goal

Production-ready path for property listing sources behind flags and legal checklist acknowledgment. Prefer licensed/API feeds; HTML scrape remains experimental and off by default.

## Must-haves

1. Complete checklist gate in UI before enabling `KEPRIX_PROPERTY_PORTAL_ADAPTERS`.
2. Adapters for licensed feed or partner API when configured; Rightmove/Zoopla HTTP only if checklist + flag + Soft Wall.
3. Rate limits, robots/ToS notes, kill switch.
4. Map listings to LeadCandidate / property sheet metrics.
5. Docs: operator legal acknowledgment text (not legal advice).
6. Tests: flag off refuse; checklist required once.

## Acceptance

- [x] Cannot enable portals without checklist ack recorded
- [x] Kill switch stops jobs mid-run safely
- [x] CSV property path still works without portals
- [x] Connections GUI configures portal flag/tokens

## Done When

Property vertical can use portals only under explicit operator risk accept.
