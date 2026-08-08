# Prompt 456 / N06: Licensed enrichment provider adapters

**Status: COMPLETED 2026-08-08**
**Series:** 429-465
**Depends on:** 433, 434, provenance from Must
**Blocks:** none
**Writing style:** plain ASCII only.

## What was built

- Provider interface + Soft Wall apply path (`licensed_enrich.py`)
- Fake licensed provider + Clearbit slot (honest empty live client)
- Workspace Connections GUI/API for Clearbit / fake enrich keys and flags (`/crm/settings#connections`)
- Docs: `docs/features/crm-connections.md`
- Tests: `tests/crm/test_connections.py`, Nice P5 enrich coverage
- Operator step remaining: enter licensed provider key in Connections, then use `/crm/enrich`

## Goal

Bring-your-own licensed enrichment providers through the same provenance contract as sheet_preprocess (empty cells only, Soft Wall apply, labelled source).

## Must-haves

1. Provider interface: `enrich_contacts(batch) -> field patches + evidence + license_tag`.
2. Config slots for owner-supplied API keys (vault); no default Clearbit scrape.
3. Provenance: each filled field stores `source=provider:name`, `evidence_url|id`, `verified=false|true`.
4. Soft Wall batch apply with diff UI (reuse 434).
5. Budget/rate limits per provider; cost metric to analytics.
6. Docs: how to plug a provider; legal note that operator must have license rights.
7. Tests: fake provider; provenance persisted; overwrite blocked.

## Acceptance

- [x] Fake provider fills blanks with provenance
- [x] Missing key returns not configured
- [x] Soft Wall reject leaves rows unchanged
- [x] Connections GUI stores encrypted Clearbit key without leaking plaintext

## Done When

LLM enrich and licensed enrich share one apply path.
