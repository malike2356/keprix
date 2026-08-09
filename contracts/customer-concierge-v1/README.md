# Customer Concierge v1 contract

**Keprix vendored copy** of Customer Concierge v1 (Prompt 629). Source mirror: `shared/contracts/customer-concierge-v1/`. Carina keeps an identical copy under `carina/02-backends/core.carinaai.uk/contracts/customer-concierge-v1/`. Do not import Carina.

**Status:** Checked-in baseline (Prompt 629 / shared Prompt 700)
**Version:** 1.0.0
**Architecture decision:** `/opt/lampp/htdocs/verlox/shared/workspace-governance/AIVA-KEPRIX-CUSTOMER-CONCIERGE-BOOKING.md`
**Keprix validators:** `src/keprix/customer_concierge/contract_schema.py`
**Gap audit:** `docs/architecture/customer-concierge-v1-baseline-audit.md`

## Purpose

This folder is the versioned **behavior contract** for Customer Concierge. Carina/Aiva and Keprix implement it independently. Contract parity means equivalent schemas, state transitions, events, security invariants, and conformance fixtures. It does **not** mean a shared database or a cross-product network dependency.

## Canonical locations

| Location | Role |
| --- | --- |
| `carina/02-backends/core.carinaai.uk/contracts/customer-concierge-v1/` | Carina checked-in copy (this tree); validated by Vitest |
| `shared/contracts/customer-concierge-v1/` | Cross-product mirror for Keprix and other consumers (no runtime import) |

When schemas change, update **both** trees in the same change set, or copy from shared into each product. Never `import` Carina TypeScript into Keprix (or the reverse).

## Compatibility and migration policy

1. **Semver.** `contractVersion` is `MAJOR.MINOR.PATCH`. Breaking schema or state-machine changes bump MAJOR. Additive optional fields bump MINOR. Clarifications and fixture-only fixes bump PATCH.
2. **Mandatory fields.** Every domain object, event, provider command, and provider result that is tenant-scoped MUST include `workspaceId` (tenant id). Every external actor reference MUST include `actorType` from the allowed set (`audience`, `operator`, `system`, `provider`). Omitting either is a conformance failure.
3. **No runtime coupling.** Products must not call each other to implement concierge. Shared knowledge is this contract and the architecture decision only.
4. **Vendor, do not import.** Keprix SHOULD vendor an identical copy of `schemas/` and `fixtures/synthetic/` under `keprix/contracts/customer-concierge-v1/` (or read the shared mirror at build/test time). Do not add a Carina package dependency.
5. **Migration window.** When MAJOR bumps, products MUST keep accepting the previous MAJOR for at least 90 days for inbound webhooks and stored event envelopes, or document an explicit cutover date in the release notes.
6. **Personal data.** Conformance fixtures MUST remain synthetic (no real emails, phones, names, or tokens). Production payloads may carry PII but must never be committed as fixtures.
7. **Honesty.** Provider readiness MUST report `not_configured` when credentials or env are absent. Never report `ready` / `connected` for a fake or stubbed provider.

## Package layout

```
customer-concierge-v1/
  README.md                          (this file)
  contract.json                      (manifest)
  schemas/
    event-envelope.schema.json
    domain-objects.schema.json
    state-machines.schema.json
    provider-commands.schema.json
    provider-results.schema.json
    readiness.schema.json
  fixtures/synthetic/                (PII-free conformance fixtures)
```

Carina TypeScript types and validators live under `src/customer-concierge/` and must stay aligned with these schemas.

## Evidence baseline

Gap audit (modules to extend): `docs/CUSTOMER-CONCIERGE-V1-BASELINE-AUDIT.md` in core.
