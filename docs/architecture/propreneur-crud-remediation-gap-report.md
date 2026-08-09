# Propreneur CRUD remediation gap report (prompt 636)

**Generated artefact:** [propreneur-crud-remediation-gap-report.json](./propreneur-crud-remediation-gap-report.json)

**Supersession (2026-08-09, prompts 637-643):** Pack invoke now exposes live reads and Soft Wall writes for contracted domains. Treat the baseline verdict below as historical. Current honesty: `GET /v1/products/propreneur/readiness`, matrix `propreneur/docs/aiva/CRUD-COVERAGE-MATRIX.md`, evidence `propreneur-e2e-evidence.v1.json`, operator UI `/settings/sidecars/propreneur`.

**Regenerate:**

```bash
cd /opt/lampp/htdocs/verlox/keprix
python3 scripts/propreneur-crud-gap-report.py
```

## Baseline verdict (2026-08-09, historical)

- Engine connectivity is built (health, token/context, Carina tool callback allowlist).
- At prompt 636, complete agent CRUD via product-pack invoke was under remediation.
- At that baseline, pack nodes were fail-closed `not_configured`; `pack_nodes_live=0`.
- Do not re-label nodes `live` without handlers, connector routes, and behavioral tests.

## Confirmed gaps (historical starting point)

See `confirmed_gaps` in the JSON report. Remediation prompts: 637-644 in `keprix-propreneur-crud-remediation` (archive under `archive/archived-prompts-library/keprix/` when complete).
