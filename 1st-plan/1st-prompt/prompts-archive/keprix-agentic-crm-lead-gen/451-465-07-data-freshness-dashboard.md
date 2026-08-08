# Prompt 457 / N07: Data freshness and quality dashboard

**Status: COMPLETED 2026-08-08** (P5 Nice)  
**Series:** 429-465  
**Depends on:** 430, 447, provenance fields  
**Blocks:** none  
**Writing style:** plain ASCII only.

## What was built

- /crm/data-quality

## Goal

Data-freshness dashboards: stale, conflicting, unverified, incomplete fields; scheduled re-verification jobs.

## Must-haves

1. Quality dimensions: completeness, staleness (last_verified_at), conflict (multi-source disagree), unverified inference.
2. Dashboard UI `/crm/data-quality` with filters by pack/stage/owner.
3. Job: re-verify selected fields via discovery/enrich adapters (Soft Wall for bulk).
4. Alerts/digest when stale % exceeds threshold.
5. Agent tool `crm_data_quality_summary`.
6. Tests: mark stale; conflict detection; job creates Soft Wall item.

## Acceptance

- [x] Incomplete email/phone lists visible
- [x] Conflicting phone from two sources flagged
- [x] Re-verify Soft Wall gated

## Done When

Operators trust CRM freshness enough to enroll.
