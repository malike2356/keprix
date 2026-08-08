# Prompt 482 / 15: Enterprise fleet admin GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/admin/fleet` with Enterprise lock, register, probe health, remove Soft Wall
- DELETE + probe fleet routes; `docs/operations/fleet.md`
- Nav admin-fleet; tests in `test_enterprise_data_gui.py`


**Depends on:** 467, existing `/api/fleet`
**Blocks:** 505

## Goal

Surface fleet instance register/list/health/audit for Enterprise operators.
API exists; no frontend clients.

## Must-haves

1. Route `/admin/fleet` (edition-gated `fleet_deploy`).
2. UI: instance table (name, base_url, version, health, alerts, last seen).
3. Actions: register, remove Soft Wall/confirm, refresh health, view alerts.
4. Honest empty state when edition lacks feature (upgrade CTA, no fake data).
5. Nav under Admin; sync contracts; hide when flag/edition off.
6. Reuse `get_fleet_manager` APIs; do not fork.
7. Tests: FE smoke with mocked edition on/off.
8. Docs: operations fleet section.

## Acceptance

- [x] Admin registers and views health from GUI when Enterprise
- [x] Non-enterprise sees honest locked state
- [x] No FE calls required via curl for day-2 fleet

## Done When

Fleet is operable from workspace admin.
