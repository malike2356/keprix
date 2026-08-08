## What was built

Superseded by Must prompt 508 workflow canvas (`/crm/workflows/[id]`).
Nice-only polish beyond 508 remains optional.

# Prompt 451 / N01: Visual workflow builder

**Status: COMPLETED 2026-08-08 (satisfied by Must 508)** (P5 Nice)  
**Series:** 429-465 Keprix agentic CRM (Nice wave)  
**Depends on:** 444 (nurture stage machine / versioned workflow model)  
**Blocks:** none  
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

**Superseded scope:** Owner promoted visual CRM to Must. Implement prompt 508
instead. It is the comprehensive superset and must use the same workflow runtime.
Do not build this as a second canvas.

## Goal

Visual workflow building that **compiles to the same versioned workflow model**
used by nurture automation (444). No second runtime. Must 466 already ships
list/pause/activate/Soft Wall publish on `/crm/workflows`; this Nice prompt
adds the canvas editor only.

## Must-haves (for this Nice prompt)

1. Canvas UI under `/crm/workflows` (nodes: delay, send email, Soft Wall gate, stage set, branch on engagement, stop).
2. Save/load versioned workflow YAML/JSON already understood by 444 runner.
3. Validate graph (no orphan sends, Soft Wall on first outbound, stop on reply).
4. Soft Wall before publishing a workflow version to production.
5. Agent can describe edits; UI remains source of truth for publish.
6. Tests: compile sample graph -> runner steps; invalid graph rejected.

## Acceptance

- [ ] Operator builds a 4-step nurture visually and enrolls a list against it
- [ ] Runner uses compiled model, not a parallel engine
- [ ] Unpublished drafts never send

## Done When

Visual edit does not fork Soft Wall sequence semantics.
