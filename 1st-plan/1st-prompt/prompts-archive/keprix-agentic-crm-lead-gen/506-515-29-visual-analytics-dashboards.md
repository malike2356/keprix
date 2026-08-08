# Prompt 512 / V07: Visual CRM analytics dashboards and charts

**Status: COMPLETED 2026-08-08**
**Series:** 506-515
**Depends on:** 447, 506, 511
**Blocks:** 513, 515
**Writing style:** plain ASCII only.

## What was built

- Visual CRM Must-thin screens under /crm/pipeline|workflows|runs|analytics|ops

## Goal

Build role-aware dashboards that explain pipeline health, acquisition,
automation, engagement, deliverability, conversion, revenue, cost, and risk.

## Must-haves

1. Executive overview includes qualified pipeline, booked opportunities,
   customers, verified revenue, spend, cost per qualified opportunity, positive
   reply rate, cycle time, and safety guardrail status.
2. Funnel view shows discovered -> contactable -> approved -> enrolled ->
   delivered -> replied -> qualified -> booked -> customer -> paying, with count,
   conversion, drop-off, median time, cohort definition, and denominator tooltip.
3. Pipeline view includes stage distribution, value, stage aging, flow over time,
   entry/exit, stalled records, owner load, and transition Sankey or flow chart.
4. Acquisition view compares source and domain pack by valid-contact yield,
   verification, qualification, conversion, cost, freshness, and policy blocks.
5. Outreach view shows sends, delivery, bounce, complaint, unsubscribe, reply,
   positive reply, cadence, template cohort, provider, and sender-domain health.
6. Workflow view shows runs, throughput, node conversion, waiting time, failure
   rate, retries, approvals, human takeover, bottlenecks, tokens, and cost.
7. Revenue view separates sourced, influenced, and manually verified outcomes.
   It exposes unverified or missing revenue events rather than estimating silently.
8. Data quality/compliance view shows duplicates, stale fields, conflicting
   evidence, low-confidence fills, retention due, suppressions, consent basis,
   complaints, and adapter/source policy blocks.
9. Global controls: date range, cohort, comparison period, campaign, workflow,
   source, pack, channel, owner, stage, and saved dashboard view.
10. Every chart supports tooltip definition, accessible summary, keyboard focus,
    underlying-data table, drill-down, filter propagation, and CSV export when
    authorised. Clicking a segment opens the exact filtered records.
11. Use appropriate visual forms: KPI cards for totals, funnel for conversion,
    line/area for trends, bars for comparisons, heatmaps for aging/time, Sankey
    only for meaningful flows, and tables for precise audit detail.
12. Avoid 3D charts, deceptive axes, unlabeled dual axes, excessive animation,
    fake precision, and red/green-only semantics.
13. Show freshness time, partial-data warnings, sampling, definition/version,
    timezone, currency, and unavailable metrics directly on the dashboard.
14. Dashboard layout is responsive, printable, and shareable through permission-
    checked saved views. Public links are out of scope unless separately approved.
15. Tests use deterministic fixtures and assert chart queries, drill-down totals,
    empty states, permission boundaries, exports, and accessibility.

## Nice-to-haves

- Annotation overlays for campaign launches or workflow changes.
- Goal/target bands and operator-entered forecasts with clear provenance.
- Scheduled PDF/email digest rendered from the same metric definitions.

## Acceptance

- [x] Users can move from headline metric to exact contributing records
- [x] Funnel and revenue totals reconcile with the semantic layer
- [x] Compliance and deliverability risks are as visible as revenue
- [x] Charts have accessible table equivalents and honest incomplete-data states

## Done When

The CRM has decision-grade visual analytics rather than decorative charts.
