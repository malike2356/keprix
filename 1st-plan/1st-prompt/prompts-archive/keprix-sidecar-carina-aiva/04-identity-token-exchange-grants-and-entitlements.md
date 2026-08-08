# Prompt 520 / CAS-04: Identity, token exchange, grants, and entitlements

**Status: COMPLETED 2026-08-08**
**Series:** 516-531
**Depends on:** 519, KSF-02
**Blocks:** 521-531
**Writing style:** plain ASCII only.

## Goal

Replace long-lived shared bearer as the only control with short-lived product
tokens that name tenant, actor, grants, purpose, and audience.

## Must-haves

1. Keep bootstrap shared secret in vault for exchange only; prefer workload
   identity in production.
2. Token claims: product, deployment, workspace/tenant, actor, roles, grants,
   purpose, session, audience, iat/exp, kid.
3. Validate issuer, audience, signature, expiry, revocation, replay.
4. Map Carina/Aiva entitlements/SKUs to node grants (Aiva worker plans vs Carina
   platform admin). Missing entitlement fails closed.
5. Cache grants briefly; refresh on deny for writes.
6. Audit every exchange, deny, and elevate attempt.
7. Migrate docs from "shared token only" to exchange flow; temporary compat mode
   documented with expiry plan.
8. Tests: expired token, wrong audience, cross-tenant grant forgery, entitlement miss.

## Acceptance

- [ ] Write invoke without grant is denied
- [ ] Aiva SKU cannot call Carina admin-only nodes
- [ ] Compat shared-token mode is flagged deprecated in health/capabilities

## Done When

521 can dual-run chat under scoped tokens.

## What was built

- Product sidecar `/v1/products/{carina|aiva}` with capability catalog
- Southbound Carina `/api/keprix/v1/*`, token exchange, Soft Wall, shadow, OPS probe
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py`
- Docs: gap map, security, sign-off, operator migration
