# Prompt 508 / V03: Graphical workflow canvas and builder

**Status: COMPLETED 2026-08-08**
**Series:** 506-515
**Depends on:** 431, 435, 436, 442-445, 451, 466, 506
**Blocks:** 509, 510, 515
**Writing style:** plain ASCII only.

## What was built

- Visual CRM Must-thin screens under /crm/pipeline|workflows|runs|analytics|ops

## Goal

Provide a node-and-edge canvas for viewing and authoring the full agentic CRM
workflow, including triggers, agent actions, human approvals, decisions, waits,
outreach, replies, bookings, goals, stops, and failures.

## Must-haves

1. Implement a workflow graph domain model independent of the canvas library:
   stable node/edge ids, typed configuration, ports, conditions, coordinates,
   schema version, workflow version, status, and migration support.
2. Canvas supports pan, zoom, fit, minimap, search, selection, multi-select,
   connect, disconnect, duplicate, align, distribute, undo, redo, and auto-layout.
3. Node palette groups triggers, data, decisions, controls, communications,
   human work, integrations, outcomes, and error handling.
4. Required nodes include:
   - Manual/channel/schedule/list/import/reply triggers.
   - Discovery, spreadsheet analysis, enrichment, dedupe, and CRM update.
   - If/else, score threshold, contactability, consent, and stage decisions.
   - Soft Wall approval, human task, wait-until, delay, and quiet-hours wait.
   - Email, Telegram operator alert, booking offer, stage transition, assignment.
   - Reply received, goal reached, suppression, stop, retry, fallback, and error.
5. Clicking a node opens a typed inspector with purpose, inputs, outputs,
   configuration, credentials reference, policy, cost estimate, sample data,
   validation, runtime history, and documentation.
6. Edges have readable condition labels. The editor detects unreachable nodes,
   missing paths, loops without limits, absent stop conditions, unsafe sends,
   missing approval, unhandled errors, and incompatible input/output schemas.
7. Draft, validate, simulate, publish, activate, pause, retire, clone, import,
   and export are explicit lifecycle operations. Editing active workflows creates
   a new draft version; running executions stay pinned to their original version.
8. Publishing shows a semantic diff and impact preview. Material changes to
   audience, content, cadence, channel, sender, or policy invalidate approvals.
9. Offer templates for lead discovery, sheet-to-CRM, cold outreach, nurture,
   reply-to-booking, stale-lead reactivation, and human handoff. Templates are
   safe starting points, never auto-active.
10. Simulation uses fixture or redacted sample data, cannot send externally,
    estimates branch counts/cost, and explains which gates would block.
11. Autosave drafts with conflict detection. Published versions are immutable.
12. Store credentials as references only. Never render secret values in nodes,
    graph exports, screenshots, logs, or simulation payloads.
13. Mobile and screen-reader users receive an equivalent ordered outline editor
    with node reorder, condition edit, validation, and inspector access.
14. Audit create/edit/publish/activate/pause actions and preserve actor/reason.

## Nice-to-haves

- Subflows and reusable organisation-approved components.
- Collapsible groups, annotations, sticky notes, and owner comments.
- Natural-language workflow drafting that always lands as an untrusted draft.

## Acceptance

- [x] User can understand the entire workflow from trigger to stop visually
- [x] Unsafe or incomplete graphs cannot publish
- [x] Active executions stay pinned when a new workflow version is published
- [x] Simulation produces no external side effects

## Done When

The graph is a durable executable definition, not decorative frontend state.
