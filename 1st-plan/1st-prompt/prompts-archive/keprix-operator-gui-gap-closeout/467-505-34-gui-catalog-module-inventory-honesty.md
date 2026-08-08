# Prompt 501 / 34: gui_catalog + module inventory honesty (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- gui_catalog extras for series surfaces + missing_gui/integration counts


**Depends on:** 468-500 (as each lands)
**Blocks:** 502, 505

## Goal

`gui_catalog.py` defaults unknown features to `cli_api` and currently marks most
mapped modules `available`, understating real API-without-GUI. Fix honesty.

## Must-haves

1. Extend `_FEATURE_GUI` / discovery mapping for every surface in this series:
   `available` | `partial` | `cli_api` | `missing_gui`.
2. Developer module inventory UI shows missing_gui list from catalog.
3. After each wave, update statuses (do not leave Tool ACL as available via wrong
   page).
4. Tests that critical APIs in inventory cannot claim `available` without href.
5. Docs note on catalog semantics.

## Acceptance

- [x] Catalog lists Tool ACL, fleet, companion, data plane, jobs, ML, export
      correctly before and after GUI ships
- [x] Module inventory exposes missing_gui

## Done When

Feature discovery stops lying about GUI coverage.
