# Prompt 447 / 18: Funnel analytics and digests

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 443, 444  
**Blocks:** 450  
**Writing style:** plain ASCII only.

## What was built

- Implemented in crm/ Soft Wall glue + UI + tests (442-448 wave)

## Goal

Operators see discovery -> enroll -> engage -> book -> paying metrics in workspace analytics.

## Must-haves

1. Extend Soft Wall / aiva_analytics metrics: lists_created, leads_discovered,
   enrolled, replied, booked, customers, paying, complaints, unsubscribes,
   enrichment_cost.
2. UI cards on `/crm` overview and `/analytics` with period selector reuse.
   Digests alone are not enough for Must.
3. Digest payload for Telegram/email (446) with deep links into `/crm/*`.
4. Per-pack and per-campaign breakdown (filterable in GUI).
5. Cost of enrichment jobs (token estimate) visible on `/crm` and `/crm/jobs`.
6. Tests for metric increments.
7. Deliverability health summary strip links to `/crm/deliverability` (466).

## Acceptance

- [x] Funnel numbers move when fixtures run enroll/reply/book
- [x] Empty workspace shows zeros not fake demos
- [x] Digest renders without crashing
- [x] `/crm` overview shows live funnel cards without leaving to Telegram

## Done When

Owners can judge ROI of agentic CRM.
