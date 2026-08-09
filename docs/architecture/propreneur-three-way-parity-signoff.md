# Keprix architecture note: Propreneur three-way parity sign-off

**Date:** 2026-08-09  
**Scope:** Programme prompts 30-35  
**Verdict:** PARTIAL

Canonical detailed receipt (may reference Contabo paths):  
`/opt/lampp/htdocs/verlox/.access/reports/propreneur-parity/2026-08-09-three-way-parity-signoff.md`

Public summary: `propreneur/docs/operations/THREE-WAY-PARITY-SIGNOFF.md`

Approved SHA `a57f24f703d46b1543374c9d37e4653fbb09ff1a` is live on Contabo with healthy app, queue, scheduler, and Keprix sidecar. Hosted CI and soak completion remain owner gates. Contabo-only `brain/masterbrain` is a time-bounded exception until the next tracked release.

## Correction (2026-08-09, prompt 636)

Preserve the historical PARTIAL deploy/health evidence above. Additional honesty correction:

- Engine connectivity (pack install, health, token/context routes, Carina tool callback allowlist) is built.
- Complete agent-driven CRUD via `/v1/products/propreneur/invoke` is **under remediation**.
- Pack nodes such as `property_get` must report `not_configured` (fail-closed), never `live`, while handlers/connector Aiva CRUD routes/behavioral tests are missing.
- Machine-readable inventory: `docs/architecture/propreneur-crud-remediation-gap-report.json`
- Programme: `1st-plan/1st-prompt/pending-prompts/keprix-propreneur-crud-remediation/`
