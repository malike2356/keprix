# Programme 00 governance baseline (public pointer)

**Date:** 2026-08-09  
**Status:** COMPLETED (read-only)

Full inventory JSON and divergence/risk reports live under protected workstation storage:

- `.access/reports/propreneur-parity/2026-08-09-programme-00-inventory.json`
- `.access/reports/propreneur-parity/2026-08-09-programme-00-divergence-and-risk.md`
- `.access/reports/propreneur-parity/2026-08-09-programme-00-execution-plan.md`

## Snapshot

| Product | Local HEAD | Contabo identity |
| --- | --- | --- |
| Propreneur | `a57f24f7…` | same release SHA + receipt |
| Keprix | `093f17c5…` | Docker `keprix-backend` healthy on `127.0.0.1:13333` |
| Carina | `ff4558b6…` | `core.carinaai.uk` Docker stack; marketing nginx 200 |

Public health: propreneur.uk, carinaai.uk, app.keprixai.com API health all HTTP 200 at collection time.

Implementation series 10-35 are archived. Residual owner gates: GitHub Actions billing, soak completion, brain-in-git release, push of local dirty ops/Aiva tree, owner sign-off tables, `OWNER-CONFIGURATION-AND-CUTOVER.md`.

## Correction (2026-08-09, prompt 636)

The 2026-08-09 read-only inventory remains historical evidence of deploy/health parity. It does **not** prove complete agent-driven Propreneur CRUD via Keprix pack invoke.

- Re-audit gap report: `docs/architecture/propreneur-crud-remediation-gap-report.json`
- Capability honesty is fail-closed: missing handlers => `not_configured`, never `live`.
- Follow-on programme: `1st-plan/1st-prompt/pending-prompts/keprix-propreneur-crud-remediation/` (prompts 636-644).
