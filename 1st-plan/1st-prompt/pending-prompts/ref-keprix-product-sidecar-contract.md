# Reference: Keprix product-sidecar contract

**Status:** BINDING FOR PETRACLUS, ABBIS, XECLONE, FLEETZ, AND CLINICOM
**Date:** 2026-08-08
**Writing style:** plain ASCII only.

## Boundary

Keprix supplies agent reasoning, product packs, tools, memory, jobs, channels,
policy, approvals, and audit. Each product remains the source of truth for its
users, tenancy, entitlements, records, billing, domain workflows, and UI.
Keprix never receives unrestricted database access and never becomes a hidden
product backend.

## Required deployment modes

1. Dedicated sidecar per product deployment, preferred for production.
2. Shared Keprix runtime with hard workspace and product namespaces, allowed only
   after isolation tests prove that one product cannot enumerate another.
3. Local development sidecar with fixture credentials and no production egress.
4. Air-gapped or offline degraded mode where the product requires it.

## Northbound Keprix HTTP contract

Each pack mounts under `/v1/products/{product_key}` and exposes:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness, readiness, dependency and degraded state |
| GET | `/capabilities` | Contract version, nodes, tools, schemas, live/stub status |
| GET | `/manifest` | Pack version, product compatibility, policy and migrations |
| POST | `/sessions` | Create scoped agent/session context |
| POST | `/invoke` | Invoke one advertised synchronous tool |
| POST | `/jobs` | Start an asynchronous capability |
| GET | `/jobs/{job_id}` | Job status, progress, checkpoints, result references |
| POST | `/jobs/{job_id}/cancel` | Idempotent cancellation |
| POST | `/events` | Signed product event ingestion with dedupe |
| GET | `/events/stream` | Optional scoped SSE/WebSocket run-event stream |
| POST | `/approvals/{id}/decision` | Signed approval or rejection when product owns UI |
| GET | `/metrics` | Product-scoped sidecar operational metrics |

Do not expose a generic arbitrary tool executor. `/invoke` validates the named
capability against the installed pack, caller grant, tenant, actor, purpose,
schema, policy, budget, and current product entitlement.

## Southbound product API connector

Each product exposes an authenticated service API for Keprix. The pack manifest
declares every allowed operation with method, path template, purpose, sensitivity,
required grant, rate limit, idempotency behaviour, approval rule, and response
schema. Default deny applies to any route not declared.

Minimum product endpoints:

- `GET /api/keprix/v1/health`
- `GET /api/keprix/v1/capabilities`
- `POST /api/keprix/v1/token/exchange` or workload-identity equivalent
- `GET /api/keprix/v1/context`
- `POST /api/keprix/v1/events/ack`
- Product-specific read endpoints with cursor pagination and field projection
- Product-specific action endpoints with idempotency keys and approval evidence

The connector must not scrape internal UI routes or call undocumented private
endpoints. Direct SQL credentials are prohibited.

## Identity, tenancy, and grants

1. Product-issued short-lived service token names product, deployment, tenant,
   user/actor, roles, grants, purpose, session, audience, issue/expiry times, and
   key id. Validate issuer, audience, signature, expiry, revocation, and replay.
2. Exchange long-lived bootstrap identity for short-lived tokens. Store bootstrap
   secrets in the existing Keprix vault, never manifests or product rows.
3. Every request carries correlation id, tenant/workspace id, actor id, purpose,
   requested capability, and least-privilege scopes.
4. Product remains authoritative for membership and entitlement. Keprix caches
   only briefly and fails closed for writes when authority cannot be checked.
5. Human approvals are scoped to exact action/input hashes and expire. Material
   changes invalidate approval.

## Capability-node manifest

Every node declares:

- stable key, version, title, product and domain;
- sync or async execution and input/output JSON Schema;
- read, propose, mutate, outbound, destructive, or high-risk classification;
- required product grants, entitlements, approvals, and feature flags;
- accepted context slices and emitted events;
- cost, timeout, concurrency, retry, idempotency, and cancellation policy;
- data classes read/produced, retention, redaction and residency;
- model/provider requirements and deterministic fallback;
- health dependencies, live/stub/degraded status and operator guidance.

Nodes compose into playbooks, but a playbook cannot elevate the grants of its
caller or bypass a node's approval, policy, budget, or product-side validation.

## Data minimisation and memory

1. Products send purpose-limited context slices, not entire records by default.
2. Keprix memory namespaces include product, deployment, tenant, subject, pack,
   and retention class. Cross-product retrieval is impossible by construction.
3. Sensitive fields are excluded from prompts unless a capability explicitly
   requires them and policy permits it. Logs contain ids and classifications,
   not raw findings, patient text, biometric media, or live telemetry.
4. Every generated fact stores provenance, source record/version, timestamp,
   model/version where relevant, confidence, verification, and expiry.
5. Product deletion and retention events propagate to Keprix indexes, caches,
   jobs, generated artifacts, and memory, with auditable completion.

## Events, jobs, and reliability

1. Events use CloudEvents-style envelopes with stable id, type, version, source,
   subject, tenant, occurred time, correlation, trace, schema, and sensitivity.
2. Delivery is at least once. Consumers dedupe by product/deployment/event id.
3. Webhooks are signed with timestamp tolerance and replay protection.
4. Async jobs persist state, checkpoint, attempts, next retry, budget, progress,
   result references and dead-letter reason. Product restart cannot lose them.
5. External side effects use a transactional outbox and idempotency key. Retry
   cannot duplicate a notification, remediation, post, command, or write.
6. Circuit breakers, bounded exponential backoff, dependency timeouts, queue
   limits, load shedding, cancellation and kill switches are mandatory.
7. Product core remains usable during Keprix outage. Product queues optional
   eligible requests or provides deterministic fallback and labels degraded state.

## Security baseline

- TLS in transit; mTLS or signed workload tokens in production.
- Bind sidecar privately; no public anonymous invoke endpoint.
- Strict request/body/file limits and schema validation.
- SSRF and egress allowlist controls for every URL or target.
- Prompt-injection controls treat product and fetched content as untrusted data.
- Tool output validation and policy recheck before every side effect.
- No shell, browser, network, filesystem, mutation, or arbitrary code node unless
  explicitly allowlisted for that product and isolated in an appropriate sandbox.
- Immutable audit for token exchange, read, inference, tool use, approval, action,
  result, denial, export, retention and administrative configuration.
- Per-product, tenant, node and provider kill switches.

## Provisioning contract

Provision is declarative and idempotent:

1. Verify product compatibility and contract versions.
2. Create product/deployment namespace and encryption keys.
3. Register workload identity, callback URLs and signing keys.
4. Install pinned pack and validate checksum/signature.
5. Apply pack migrations and memory/index policy.
6. Register capability nodes, tools, playbooks, events and product connector.
7. Validate grants against product `/capabilities`.
8. Run read-only contract smoke, negative isolation and denied-write tests.
9. Activate feature flag only after operator approval.
10. Emit provision receipt with versions and rollback instructions, no secrets.

Upgrades use expand/migrate/contract, retain last-known-good pack, support dry-run
and rollback, and never auto-enable newly risky capabilities.

## Definition of ready

A product sidecar is not ready until:

- health and capability negotiation pass;
- every advertised live node has contract and policy tests;
- reads are projected, paginated and tenant-scoped;
- writes are idempotent, product-validated and approval-gated;
- sidecar outage leaves product core working;
- cross-product and cross-tenant tests fail closed;
- deletion/retention propagation passes;
- prompt injection, SSRF, replay, forged token and oversized request tests pass;
- load, timeout, retry, cancellation, dead-letter and rollback drills pass;
- product-specific owner signs a capped staging pilot before production.
