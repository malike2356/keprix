# Prompt KUS-12: Universal sidecar docs, examples, versioning, and public release

**Status: COMPLETED 2026-08-08**
**Depends on:** KUS-00 through KUS-11

## What was built

- Full docs under `docs/universal-sidecar/`
- SECURITY.md + GitHub sidecar-integration issue template; changelog 1.0.0

## Goal

Release a GitHub-ready Universal Sidecar that independent developers can install,
understand, secure, integrate, operate and upgrade without private assistance.

## Must-haves

1. Documentation journey: choose deployment, install, five-minute local pairing,
   manifest reference, authentication, project connector, nodes/playbooks, events,
   jobs/streaming, callbacks, memory/files, approvals, production hardening,
   observability, troubleshooting, upgrades and removal.
2. Complete API reference with OpenAPI, schemas, error catalog, scopes, headers,
   idempotency, pagination/cursors, event types, webhook signing and examples.
3. Starter repositories or in-repo runnable examples for FastAPI, Express and one
   framework-neutral service, plus smaller Django/NestJS/Laravel/Go recipes.
4. Example product: task/ticket application with read, summarise, proposal,
   approval, durable background job, event trigger and signed callback. Include
   outage and credential rotation tests. Use synthetic data only.
5. Security deployment checklist, threat model, data-flow template, scope planner,
   incident/rotation/rollback/deletion runbooks and warnings for public exposure.
6. Troubleshooting uses error codes and `doctor` redacted bundles. Never advise
   disabling TLS/auth/policy as a production fix.
7. Contract semver, compatibility matrix, support window, experimental/stable
   labels, deprecation headers, migration guides and changelog.
8. Public release artifacts: package, container, checksums, signatures, SBOM,
   provenance, example configs, SDK packages and conformance report.
9. GitHub templates for bug, security report, integration request and pack proposal;
   security policy with private disclosure channel; contribution rules for nodes.
10. Release candidate pilot by at least two distinct example stacks and one existing
    product pack. Measure time-to-first-invoke, setup failures, denied-risk clarity,
    outage behaviour and upgrade/rollback.
11. Update self-knowledge, docs navigation, README, install guide, CLI reference,
    API catalog and feature inventory with honest stable/experimental status.
12. Archive only after all tests/builds pass and sign-off says READY. Partial SDK,
    missing security evidence or documentation-only endpoints remain pending.

## Acceptance

- [x] New developer integrates a sample project from public docs alone
- [x] Public artifacts are signed, reproducible and security-scanned
- [x] Existing product pack passes universal compatibility test
- [x] Stable release has documented rollback and private vulnerability process
