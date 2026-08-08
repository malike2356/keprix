# Prompt 506 / V01: Visual CRM information architecture and design contract

**Status: COMPLETED 2026-08-08**
**Series:** 506-515 Keprix visual agentic CRM Must sprint
**Depends on:** 429, 431, 432, binding hardening review
**Blocks:** 507-514
**Writing style:** plain ASCII only.

## Why this exists

The CRM cannot be a collection of tables and API routes. Users need distinct
visual answers to three questions: where each lead is now, what automation is
configured to happen next, and what the agent is doing or waiting for.

## What was built

- Visual CRM Must-thin screens under /crm/pipeline|workflows|runs|analytics|ops

## Goal

Lock the information architecture, visual language, interaction model, and data
contracts for pipeline, workflow, execution, and analytics surfaces before the
individual screens are built.

## Must-haves

1. Define four linked surfaces:
   - Pipeline board: records grouped by lifecycle or deal stage.
   - Workflow canvas: versioned nodes and edges describing future behaviour.
   - Execution view: live and historical runs moving through those nodes.
   - Analytics dashboard: outcomes, conversion, speed, cost, quality, and risk.
2. Publish route plan: `/crm`, `/crm/pipeline`, `/crm/workflows`,
   `/crm/workflows/[id]`, `/crm/runs/[id]`, `/crm/analytics`.
3. Define canonical visual entities and API view models. UI must not infer state
   by joining unrelated endpoints in the browser.
4. Define node families: trigger, discovery, enrich, decision, approval, wait,
   outreach, reply, stage, booking, human task, integration, goal, stop, error.
5. Define state language: draft, ready, active, waiting, approval_required,
   paused, succeeded, partially_succeeded, failed, cancelled, suppressed.
6. Define consistent colours, shapes, icons, labels, edge styles, badges, and
   motion meanings. Colour cannot be the only carrier of meaning.
7. Define navigation among a lead, list, campaign, workflow, run, activity,
   approval, booking, source evidence, and analytics segment.
8. Define desktop, tablet, and mobile behaviour. Mobile may use an ordered step
   view instead of forcing a miniature canvas.
9. Define permissions for view, edit, publish, activate, pause, approve, replay,
   export, and dashboard configuration.
10. Include low-fidelity wireframes and real-data empty, loading, partial,
    blocked, error, and permission-denied states.
11. Reuse Keprix theme tokens and existing workspace shell. Do not introduce a
    standalone design system or a permanent second leads UI.
12. Apply the hardening review: workspace isolation, provenance, audit,
    idempotency, contactability, suppression, and kill-switch states are visible.

## Acceptance

- [x] Architecture doc distinguishes pipeline, definition, execution, and analytics
- [x] Every surface has routes, data contracts, permissions, and mobile behaviour
- [x] Visual legend is accessible and consistent
- [x] Blocked, waiting, suppressed, and human-owned states are first-class

## Done When

Prompts 507-514 can implement without inventing incompatible visual semantics.
