# Prompt 440 / 11: Property vertical pack (flagged)

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 436, 433  
**Blocks:** 449  
**Writing style:** plain ASCII only.

## What was built

- src/keprix/discovery/ adapters + Soft Wall materialize
- /crm/discover + /crm/jobs UI
- tests/discovery


## Goal

Property domain pack: sheet types, metrics, and discovery adapters that are legally gated.

## Must-haves

1. Pack manifest `packs/property/` or `domain_packs/property.yaml`: sheet types, column presets, stage labels.
2. Spreadsheet types: `property_data`, `tenant_list`, `landlord_pipeline` with metric presets (beds, rent, yield, EPC, etc.).
3. Adapters:
   - `property_csv` (always on)
   - `rightmove_http` / `zoopla_http` as **experimental**, default **disabled**, require `KEPRIX_PROPERTY_PORTAL_ADAPTERS=1` and Soft Wall + docs legal checklist
4. Prefer licensed/API data when available; document ToS risk for HTML scrape.
5. UI copy never claims "we scrape Zoopla" unless flag on and checklist acknowledged.
6. Tests for pack schema + disabled adapter.

## Acceptance

- [x] Property sheet preprocess works without portals
- [x] Portal adapters refuse when flag off
- [x] Checklist markdown in docs/security or docs/features

## Done When

Property users get value via CSV/CH/web without forced scrape.
