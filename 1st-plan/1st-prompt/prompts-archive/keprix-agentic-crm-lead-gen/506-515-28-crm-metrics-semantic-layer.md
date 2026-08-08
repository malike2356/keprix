# Prompt 511 / V06: CRM metrics semantic layer and event model

**Status: COMPLETED 2026-08-08**
**Series:** 506-515
**Depends on:** 430, 443-448, 506, 507
**Blocks:** 512, 513, 515
**Writing style:** plain ASCII only.

## Why this exists

Charts are misleading when every screen defines conversion, reply, customer,
cost, or attribution differently. Establish one tested semantic layer first.

## What was built

- Visual CRM Must-thin screens under /crm/pipeline|workflows|runs|analytics|ops

## Goal

Create canonical CRM events, dimensions, measures, cohorts, attribution rules,
and query endpoints used by dashboards, digests, agent Q&A, and exports.

## Must-haves

1. Canonical events include discovered, imported, enriched, verified, listed,
   approved, enrolled, attempted, delivered, bounced, complained, replied,
   positive_reply, negative_reply, unsubscribed, qualified, booked, attended,
   customer, paying, lost, suppressed, human_takeover, and workflow_failed.
2. Event fields include workspace, subject ids, campaign/workflow/version/run,
   source/pack/channel, actor, occurred/received times, idempotency key,
   correlation id, value/currency where applicable, and evidence reference.
3. Define measures precisely: unique leads, contactable rate, enrichment yield,
   verification rate, enrollment rate, delivery rate, reply rate, positive reply
   rate, qualification rate, booking rate, show rate, win rate, revenue, pipeline,
   cost per verified lead, cost per qualified lead, cycle time, and stage aging.
4. Define guard metrics: hard bounce, complaint, unsubscribe, suppression,
   failed-send, false-enrichment, duplicate, human-review, and policy-block rates.
5. Denominators are explicit and displayed in API metadata and chart tooltips.
   Opens and clicks remain optional privacy-sensitive estimates, not core truth.
6. Support dimensions for time, source, pack, campaign, workflow/version, channel,
   owner, stage, geography at safe granularity, segment, template, and provider.
7. Use event time and workspace timezone consistently. Handle late and duplicate
   events, currency conversion policy, stage re-entry, and deleted records.
8. Funnel cohorts can be first-touch, enrollment, or opportunity-created cohorts.
   Never mix cohort definitions without labelling them.
9. Attribution supports unambiguous sourced revenue first. Influenced and
   multi-touch models are separate labelled views, never silently combined.
10. Query service enforces workspace isolation, bounded date ranges, pagination,
    group limits, caching, and export permission. Results return definition ids.
11. Backfill derives events from existing Soft Wall/CRM data idempotently and
    reports gaps instead of fabricating history.
12. Data-quality tests reconcile headline totals to source records and verify
    isolation, dedupe, late events, timezone boundaries, and empty workspaces.

## Acceptance

- [x] Every headline metric has one versioned definition and denominator
- [x] Dashboard, digest, export, and crm_ask return reconciled totals
- [x] Empty or incomplete history is labelled honestly
- [x] Guard metrics can stop rollout or trigger kill-switch review

## Done When

Prompt 512 can render trusted charts without embedding business logic in React.
