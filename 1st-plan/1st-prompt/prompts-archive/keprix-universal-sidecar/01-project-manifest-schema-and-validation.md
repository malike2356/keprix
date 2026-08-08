# Prompt KUS-01: Declarative project manifest and validation

**Status: COMPLETED 2026-08-08**
**Depends on:** KUS-00
**Blocks:** KUS-02 through KUS-10

## What was built

- JSON Schema + `manifest/validate.py` (secrets/hooks/URI/SSRF checks, semantic catalog)
- CLI validate/diff/explain/plan/apply/export-redacted; example manifests under `manifest/examples/`

## Goal

Let developers configure a project safely through one portable manifest plus
vault references, with excellent validation and no hidden code execution.

## Must-haves

1. Define `keprix.sidecar.yaml` JSON Schema with: contract version, project key,
   display name, deployment/environment, base URL, callback URLs, auth profile,
   tenant/actor mapping, requested packs/nodes, connector operations, events,
   context slices, memory, approvals, budgets, retention, egress and feature flags.
2. Connector operation declares stable key, method, relative path template,
   request/response schema refs, pagination, projections, grants, sensitivity,
   timeout, rate, cache, retry/idempotency, approval and purpose.
3. Capability binding declares node/version, alias, scopes, input defaults,
   context sources, model/provider constraints, timeout, budget and UI description.
4. Events declare CloudEvents type/schema, direction, sensitivity, dedupe, delivery,
   callback and retention. Webhooks declare signature and retry requirements.
5. Secret values are prohibited. Fields accept vault/env/secret-manager references
   and validation reports whether reference exists without printing its value.
6. URI/path templates cannot contain credentials, arbitrary schemes, traversal,
   unbounded wildcards or metadata/link-local destinations.
7. Support local schema files and packaged refs under a constrained project config
   directory. Never execute templates, imports, hooks or arbitrary Python/JS.
8. Commands: `keprix sidecar init`, `validate`, `diff`, `explain`, `doctor`,
   `plan`, `apply`, `export-redacted`. Validation errors include exact path,
   reason, safe example and migration guidance.
9. Semantic validation compares requested nodes/scopes to installed capability
   catalog and runtime policy; unknown, deprecated or denied items fail honestly.
10. Define canonical minimal, read-only, read-plus-propose, async-job and event-
    driven examples with no production secrets.

## Acceptance

- [x] Minimal manifest validates and unknown capability fails
- [x] Manifest cannot embed a secret or executable hook
- [x] Diff highlights newly risky access and requires explicit apply
- [x] Redacted export is safe for support tickets
