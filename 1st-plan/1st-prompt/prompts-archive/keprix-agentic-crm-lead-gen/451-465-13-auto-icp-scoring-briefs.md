# Prompt 463 / N13: Auto ICP scoring and account briefs

**Status: COMPLETED 2026-08-08** (P5 Nice)  
**Series:** 429-465  
**Depends on:** 452, opportunity engine, 435  
**Blocks:** none  
**Writing style:** plain ASCII only.

## What was built

- ICP scoring + account briefs

## Goal

Auto ICP scoring from opportunity engine + saved ICP versions; evidence-backed account briefs and suggested personalisation angles.

## Must-haves

1. Score lead/account against active ICP version; store `icp_score`, `icp_version`, reasons[].
2. Brief generator: company summary, pains (evidence links), suggested angle; Soft Wall before mass attach to enroll copy.
3. Reuse opportunity/pain mining outputs when relevant; label inference vs verified.
4. UI: score column, brief panel on account/lead.
5. Agent tools `crm_score_icp`, `crm_account_brief`.
6. Tests: score deterministic for fixture ICP; brief cites sources.

## Acceptance

- [x] List sorted by icp_score
- [x] Brief shows evidence ids/urls
- [x] Mass brief Soft Wall gated

## Done When

Discovery quality is visible before enroll spend.
