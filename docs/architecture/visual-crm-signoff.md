# Visual CRM Must sign-off evidence (prompt 515)

**Date:** 2026-08-08
**Verdict:** READY

## Shipped routes

- `/crm/pipeline`
- `/crm/workflows` and `/crm/workflows/[id]`
- `/crm/runs/[id]`
- `/crm/analytics`
- `/crm/ops`

## API surface

- `/api/crm/visual/contract`
- `/api/crm/visual/pipeline-board` (+ preview/transition)
- `/api/crm/visual/workflows/{id}` (+ validate/simulate/publish)
- `/api/crm/visual/runs` (+ events/step/compare)
- `/api/crm/visual/inspector` and support-bundle
- `/api/crm/visual/metrics/*`
- `/api/crm/visual/ops`
- `/api/crm/visual/a11y-performance`

## Evidence

- Contract + isolation tests: `tests/crm/test_visual_crm.py`, `tests/crm/test_visual_e2e_signoff.py`
- Frontend smoke: CRM Must routes under `frontend/src/app/(workspace)/crm/`
- Operator runbook: `docs/architecture/visual-crm-operator-runbook.md`
- IA contract: `docs/architecture/visual-crm-information-architecture.md`
- Core CRM sign-off remains READY: `docs/architecture/agentic-crm-signoff.md`

## Honest deferred polish (not blocking READY)

- Full canvas multi-select, undo/redo, align/distribute
- WebSocket live transport (polling ships; topics reserved)
- Sankey/heatmap chart polish (semantic KPIs ship)
- Aggregate campaign animation mode

## Progressive rollout

Internal workspace first, capped pilot, observe guard metrics (bounce/complaint/dead-letter/kill switch), then default-on. Rollback owner: workspace admin via kill switch + workflow pause.

## Archive rule

Must prompts 429-450, 466, and 506-515 are complete. Nice prompt 451 is satisfied by 508. Unselected Nice prompts 452-465 remain pending.
