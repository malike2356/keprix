# Visual CRM information architecture (prompt 506)

**Status:** SHIPPED (Must-thin contract)
**Contract version:** 1.0.0
**Module:** `src/keprix/crm/visual_contract.py`
**API:** `GET /api/crm/visual/contract`

## Four linked surfaces

| Surface | Question | Route | View model |
| --- | --- | --- | --- |
| Pipeline board | Where is each record now? | `/crm/pipeline` | `GET /api/crm/visual/pipeline-board` |
| Workflow canvas | What automation will run? | `/crm/workflows`, `/crm/workflows/[id]` | `GET /api/crm/visual/workflows/{id}` |
| Execution view | What is happening or waiting? | `/crm/runs/[id]` | `GET /api/crm/visual/runs/{id}` |
| Analytics | Are outcomes safe and useful? | `/crm/analytics` | `POST /api/crm/visual/metrics/query` |

Ops supervision sits beside these at `/crm/ops`.

## Visual language

- Node families: trigger, discovery, enrich, decision, approval, wait, outreach, reply, stage, booking, human_task, integration, goal, stop, error.
- Runtime states: draft, ready, active, waiting, approval_required, paused, succeeded, partially_succeeded, failed, cancelled, suppressed, skipped, upcoming.
- Colour is never the only carrier of meaning. Every state has a text label and shape/icon key (`STATE_LEGEND`).
- Blocked, waiting, suppressed, and human-owned are first-class warnings on cards and nodes.

## Permissions

view, edit, publish, activate, pause, approve, replay, export, dashboard_configure.

Mapped through existing CRM role caps (`view` / `edit` / `approve` / `export` / `send`).

## Mobile behaviour

- Pipeline: horizontal lanes or stage-list toggle.
- Canvas: ordered outline editor equivalent.
- Execution: static timeline table always available.
- Analytics: KPI cards then tables.
- Inspector: side drawer / sheet with back.

## Hardening visibility

Workspace isolation, provenance labels, audit, idempotency keys, contactability, suppression, and kill-switch states appear in board cards, inspector policy tabs, ops alerts, and analytics guards.

## Empty / loading / error states

Surfaces must render honest empty, loading, partial, blocked, error, and permission-denied states. No demo data is invented for empty workspaces.

## Low-fidelity wireframes (text)

Pipeline board:

```
[Filters: search | saved view | owner]
[Discovered] [Enriched] ... [Paying]
  card         card
  card
[Inspector drawer: record | stage move | Soft Wall notes]
```

Workflow canvas:

```
[Palette] [Canvas pan/zoom] [Inspector]
 outline | graph nodes/edges | validate/simulate/publish
```

Run replay:

```
[Timeline events] [Highlighted node] [Play/pause reduced-motion]
```

Analytics:

```
[KPI cards]
[Funnel table] [Guard metrics]
[Drill-down -> exact records]
```

## Reuse

Keprix workspace shell, MUI theme tokens, Soft Wall approvals, and existing `/crm/*` tables remain. This sprint does not introduce a permanent second leads UI.
