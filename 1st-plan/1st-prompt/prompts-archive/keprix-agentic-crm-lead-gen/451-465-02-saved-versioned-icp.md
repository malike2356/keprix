# Prompt 452 / N02: Saved versioned ICP definitions

**Status: COMPLETED 2026-08-08**
**Series:** 429-465  
**Depends on:** 430, 436, opportunity engine  
**Blocks:** 463  
**Writing style:** plain ASCII only.

## What was built

- Versioned ICP store on Nice schema (`crm_icp_definitions`) via `keprix.crm.icp`
- Soft Wall activate (`icp_activate`); revise clones immutable N+1
- HTTP `/api/crm/icp*` + GUI `/crm/icp` (create/diff/activate)
- Agent tools `crm_icp_list` / `crm_icp_use`
- Discovery jobs accept `icp_id`/`icp_version`; materialize + enroll apply exclude rules
- Tests: `tests/crm/test_icp.py` (3 passed)

## Goal

Saved ICP versions with inclusion/exclusion rules used by discovery and scoring.

## Must-haves

1. Model `IcpDefinition`: name, version, pack, include rules, exclude rules, geography, size, keywords, SIC, notes.
2. Immutable versions; new edit creates version N+1; Soft Wall to set active.
3. Discovery jobs accept `icp_id` + version; store on List and leads.
4. UI: `/crm/icp` list/create/diff versions/activate.
5. Agent tool `crm_icp_list` / `crm_icp_use`.
6. Exclusion list always applied before enroll.
7. Tests: version activate; discovery tags icp version.

## Acceptance

- [x] Two ICP versions coexist; only active used by default discovery
- [x] Diff view shows rule changes
- [x] Exclusions remove matching candidates

## Done When

463 can score against a pinned ICP version.
