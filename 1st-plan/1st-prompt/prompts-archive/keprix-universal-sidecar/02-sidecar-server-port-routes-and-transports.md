# Prompt KUS-02: Sidecar server, port, routes, and transports

**Status: COMPLETED 2026-08-08**
**Depends on:** KUS-00, KUS-01, foundation HTTP prompt
**Blocks:** KUS-03, KUS-06, KUS-08

## What was built

- `keprix.universal_sidecar.routes` FastAPI router at `/sidecar/v1` (root health/ready/version/projects/architecture/openapi + project routes for sessions, pair, invoke, jobs, SSE events, approvals, metrics, kill, memory, files)
- `keprix.universal_sidecar.app` sidecar-only FastAPI process (default `127.0.0.1:3360`), lifespan shutdown flag, public-bind refuse
- `keprix.universal_sidecar.conformance` basic TestClient suite
- CLI `keprix sidecar` (init/validate/diff/explain/doctor/plan/apply/export-redacted/start/quickstart/pair/capabilities/invoke/job/watch/send-event/verify-webhook/connector-test/conformance)
- Wired into `api/server.py` and `keprix_cli/main.py`

## Goal

Provide one secure access point that works mounted on port 3333 or as a reduced
sidecar-only service on configurable private port 3360.

## Must-haves

1. CLI `keprix sidecar start --config ... --host ... --port ... --profile ...`.
   Sidecar-only profile mounts only health, discovery, sessions, invoke, jobs,
   events, approvals, metrics and required auth routes, not admin/workspace UI.
2. Universal routes under `/sidecar/v1/projects/{project_key}`: health, readiness,
   capabilities, manifest digest, sessions, invoke, jobs/status/cancel/events,
   inbound events, approval decision, metrics metadata and contract OpenAPI.
3. Include root `/sidecar/v1/health`, `/ready`, `/version`, `/projects` with project
   enumeration restricted to authorised administrative identity.
4. Transports: JSON HTTP; SSE for job/run events; optional WebSocket parity only
   when it shares event semantics; webhook callback; local in-process adapter for
   trusted embedded deployments. No transport may bypass policy.
5. Content types, request ids, correlation/trace, idempotency headers, pagination,
   cursor resume, cancellation and stable error envelope are documented.
6. Health distinguishes process liveness, config validity, project connector,
   provider, queue, storage, capability and degraded state without leaking secrets.
7. Default bind is loopback. Non-loopback without configured authentication/TLS
   refuses start unless an explicit development override displays a strong warning.
8. CORS defaults deny; browser origins are explicit. CSRF applies to cookie-based
   admin flows; machine API uses bearer/mTLS.
9. Graceful shutdown stops admission, drains safe work, checkpoints jobs and exits
   within configured deadline. Readiness goes false before termination.
10. OpenAPI is profile-aware and generated from actually enabled routes/nodes.

## Acceptance

- [x] Mounted and sidecar-only modes pass the same contract tests
- [x] Sidecar-only process does not expose unrelated Keprix administration
- [x] Public bind without secure config fails
- [x] SSE reconnect resumes without duplicate run events
