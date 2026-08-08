# Prompt 461 / N11: Social API adapters production (LinkedIn, Meta, TikTok)

**Status: COMPLETED 2026-08-08**
**Series:** 429-465
**Depends on:** 439 (stubs), 436, 448
**Blocks:** none
**Writing style:** plain ASCII only.

## What was built

- Official-API-first social adapters with scrape refusal
- Health reports missing credentials/scopes and points to Connections
- Workspace Connections slots for LinkedIn/Meta/TikTok client ids/secrets/scopes + enable flags
- Docs: `docs/features/crm-connections.md` (+ existing social discovery docs)
- Tests: LinkedIn configured after workspace credentials in `tests/crm/test_connections.py`
- Operator step remaining: enter OAuth/app credentials and enable flags, then use discover/messaging health

## Goal

Turn social discovery stubs into working **official API** adapters when owner credentials exist. Scrape remains off.

## Must-haves

1. Implement OAuth/app credential flows for LinkedIn, Meta Graph, TikTok where product APIs allow lead/org sync.
2. Map API payloads to LeadCandidate; Soft Wall before List materialize.
3. Health + setup UI showing connected / missing scopes.
4. Rate limits and egress allowlist.
5. Docs per network: required products, scopes, ToS.
6. Tests: mocked OAuth + sync; unconfigured path unchanged.

## Acceptance

- [x] Connected LinkedIn (workspace keys) reports healthy / configured
- [x] Scrape tools still refuse
- [x] Scope missing explains which permission is needed
- [x] Connections GUI is the operator config surface

## Done When

Social discovery is real for licensed API users without HTML bots.
