# API reference (`/sidecar/v1`)

Base paths:

- Mounted: `http://127.0.0.1:3333/sidecar/v1`
- Sidecar-only: `http://127.0.0.1:3360/sidecar/v1`

Project-scoped routes use `{project_key}`.

## Discovery and health

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Global sidecar liveness |
| GET | `/projects/{project_key}/health` | Project health / readiness / degraded |
| GET | `/projects/{project_key}/capabilities` | Contract version, nodes, schemas, live/stub |
| GET | `/projects/{project_key}/manifest` | Effective manifest (secrets redacted) |
| GET | `/projects/{project_key}/metrics` | Scoped operational metrics |

## Pairing and sessions

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/pair/bootstrap` | Exchange pairing code for bootstrap receipt |
| POST | `/projects/{project_key}/sessions` | Create scoped session context |

## Invoke and jobs

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/projects/{project_key}/invoke` | Synchronous declared capability |
| POST | `/projects/{project_key}/jobs` | Start async capability |
| GET | `/projects/{project_key}/jobs/{job_id}` | Job status |
| POST | `/projects/{project_key}/jobs/{job_id}/cancel` | Cancel job |

## Events and approvals

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/projects/{project_key}/events` | Ingest signed product event |
| GET | `/projects/{project_key}/events/stream` | SSE / WebSocket run-event stream |
| POST | `/projects/{project_key}/approvals/{id}/decision` | Approve or reject |

## Connectors and administration

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/projects/{project_key}/connectors/{key}/test` | Smoke-test declared connector |
| POST | `/projects/{project_key}/kill-switch` | Engage / clear project kill switch |
| GET | `/projects` | List registered projects (operator) |

All invokes validate capability against pack, grant, tenant, actor, purpose,
schema, policy, budget, and entitlement. There is no generic free-form tool
proxy.
