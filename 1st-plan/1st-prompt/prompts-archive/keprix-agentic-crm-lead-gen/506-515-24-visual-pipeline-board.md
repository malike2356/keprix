# Prompt 507 / V02: Interactive visual pipeline board

**Status: COMPLETED 2026-08-08**
**Series:** 506-515
**Depends on:** 430-432, 444, 466, 506
**Blocks:** 511, 513, 515
**Writing style:** plain ASCII only.

## What was built

- Visual CRM Must-thin screens under /crm/pipeline|workflows|runs|analytics|ops

## Goal

Build a visual Kanban-style pipeline where users can see, filter, inspect, and
safely move leads, contacts, and deals through the agentic CRM lifecycle.

## Must-haves

1. Board lanes use the canonical stage machine and show configurable stage
   name, count, total value where relevant, average age, and conversion health.
2. Cards show the minimum useful summary: account/person, fit and engagement
   signals, owner, source, last touch, next action, sequence/run state, warnings,
   consent/contactability, and deal value when present.
3. Clicking a card opens a side inspector without losing board context. It links
   to the full record, activity timeline, workflow run, evidence, and approvals.
4. Drag/drop produces a transition preview. It must validate the stage graph,
   permissions, required fields, verified business events, and Soft Wall policy
   before committing. Illegal transitions explain the reason and safe next step.
5. Support keyboard stage movement and non-drag controls with identical checks.
6. Filters: owner, pack, campaign, workflow, source, tag, score ranges,
   contactability, approval state, stale state, next-action date, and search.
7. Saved views include My pipeline, Needs review, Human takeover, Stale,
   Awaiting approval, Suppressed, Qualified, and custom workspace views.
8. Bulk actions show selected count and impact preview. Enroll, suppress, assign,
   stage change, export, and delete retain their approval and audit gates.
9. Use optimistic UI only for reversible local presentation. Confirm durable
   server state before presenting a risky external action as complete.
10. Handle concurrent edits with version conflicts and a compare/reload choice.
11. Large pipelines use server pagination or virtualisation without inaccurate
    lane totals. Filters and sort state are URL-addressable.
12. Optional compact transition animation moves a card only after success.
    Respect reduced-motion settings and never animate fake progress.
13. Mobile uses horizontally scrollable lanes or a stage-list mode with a clear
    switch. Card actions remain touch-safe and accessible.
14. Tests cover isolation, transition denial, verified paying transition,
    approval creation, keyboard movement, concurrency, and large datasets.

## Nice-to-haves

- Swimlanes by owner, campaign, or deal type.
- WIP limits and stage service-level warnings.
- Forecast view using explicit weighted values, not unexplained AI prediction.

## Acceptance

- [x] User can understand pipeline state without opening a table
- [x] Card click exposes state, history, next action, and workflow context
- [x] Drag and keyboard transitions enforce identical server rules
- [x] Suppressed and human-owned records cannot be accidentally automated

## Done When

The pipeline is the primary operational view while tables remain available for
dense review and export.
