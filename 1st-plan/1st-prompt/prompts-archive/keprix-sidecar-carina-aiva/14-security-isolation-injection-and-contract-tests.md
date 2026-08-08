# Prompt 530 / CAS-14: Security, isolation, injection, and contract tests

**Status: COMPLETED 2026-08-08**
**Series:** 516-531
**Depends on:** 518-527
**Blocks:** 531
**Writing style:** plain ASCII only.

## Goal

Prove the Carina/Aiva sidecar integration is safe enough for default-on pilots.

## Must-haves

1. Contract suite: health, capabilities, invoke allow/deny, jobs cancel, events
   dedupe, approval resume.
2. Isolation: cross-workspace REST, memory, jobs, CRM, Soft Wall, SSE topics.
3. Authn/z: forged token, expired token, wrong audience, replay.
4. Prompt injection: tool output and product content treated as untrusted; cannot
   self-approve Soft Wall or exfiltrate secrets.
5. SSRF/egress allowlist on any URL-bearing node.
6. Oversized body and rate limit tests.
7. No shell/browser/arbitrary code nodes unless explicitly allowlisted and sandboxed.
8. Record evidence in `docs/architecture/carina-aiva-keprix-sidecar-security.md`.

## Acceptance

- [ ] All isolation tests fail closed
- [ ] Injection suite cannot bypass Soft Wall
- [ ] Security doc lists residual risks honestly

## Done When

531 can cite a green security gate.

## What was built

- Product sidecar `/v1/products/{carina|aiva}` with capability catalog
- Southbound Carina `/api/keprix/v1/*`, token exchange, Soft Wall, shadow, OPS probe
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py`
- Docs: gap map, security, sign-off, operator migration
