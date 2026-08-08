# Archived: Keprix sidecar for Carina + Aiva (CAS 516-531)

**Status: COMPLETED 2026-08-08**

## What was built

- Northbound `/v1/products/{carina|aiva}` (health, capabilities, invoke, jobs, events, approvals)
- Packs carina + aiva wrapper; Soft Wall product-owned; southbound allowlist
- Token exchange (shared-token compat deprecated); shadow dual-run; OPS invoke probe
- Docs under `docs/architecture/carina-aiva-keprix-sidecar-*.md`
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py` (17 passed)

Sign-off: `docs/architecture/carina-aiva-keprix-sidecar-signoff.md` (READY local/staging pilot).
Owner-gated Nice nodes remain `not_configured`.
