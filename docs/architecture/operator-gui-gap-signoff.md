# Operator GUI gap closeout sign-off (505)

**Date:** 2026-08-08
**Series:** 467-505

## Verdict

Must surfaces from the operator GUI gap inventory are now reachable from the
workspace GUI (or explicitly registered as intentional non-GUI). Soft Wall
confirm remains the default gate for side-effecting operator actions.

## Validation run

- `pytest tests/frontend/test_enterprise_data_gui.py`
- `pytest tests/frontend/test_platform_depth_gui.py`
- `pytest tests/frontend/test_findability_honesty.py`
- `pytest tests/frontend/test_discovery_crm_gate.py`
- `pytest tests/jobs/test_cancel_retry.py`
- `pytest tests/fleet/test_manager.py`

## Key routes shipped

Admin: Tool ACL, fleet, companion, code-agent, typed agents, kernel, interfaces,
intent, tool adapters, personas, workspace-ops.

Data: datasets, jobs, ml, export.

Agent OS: improvements Soft Wall review.

Findability: document-agents, commerce billing/upgrade, leads/opportunities
clarity, gui_catalog honesty, credential proxy ops panel.

## Residual / intentional

See Intentional non-GUI register in `operator-gui-gap-inventory.md`. CRM sibling
depth beyond the 481 gate remains owned by `keprix-agentic-crm-lead-gen`.
