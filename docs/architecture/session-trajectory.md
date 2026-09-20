# Session trajectory (append-only + fork / replay)

**Status:** Implemented (prompt 770, 2026-09-20)
**Package:** `keprix.trajectory`
**UI:** `/trajectory` (nav id `trajectory`)
**API:** `/api/trajectories`

## Intent

Strengthen the session event log into an append-only **trajectory** operators can
search, fork, and replay. Use it to debug Soft Wall denials, Mutation Engine
failures, and agent loop faults.

Steal the DeepSeek Harness trajectory *idea*. Do not import Cordis. Do not
replace Scout or full observability stacks.

## Event types

`message`, `tool_call`, `tool_result`, `soft_wall`, `mutation`, `error`,
`checkpoint`, `note`.

Corrections are **new events**. Past rows cannot be UPDATE/DELETE'd
(`AppendOnlyViolation`).

## Persistence

SQLite under `{KEPRIX_HOME}/trajectories/trajectories.db` (override via store
constructor for tests). Trajectories are workspace-scoped.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/trajectories` | List |
| POST | `/api/trajectories` | Create |
| GET | `/api/trajectories/{id}` | Get + events |
| POST | `/api/trajectories/{id}/events` | Append |
| GET | `/api/trajectories/search` | Filter by type/tool/Soft Wall/error |
| POST | `/api/trajectories/{id}/fork` | Clone prefix through `through_seq` |
| POST | `/api/trajectories/{id}/replay` | Recorded (default) or live-gated plan |

## Replay modes

- **recorded** (default): returns steps with `use_recorded_result=true` and
  `execute=false`. Safe for Soft Wall / mutation debugging without live shell.
- **live**: marks dangerous tool steps with `requires_soft_wall=true`; does not
  auto-execute shell/fs.

## Redaction

Payloads pass through `redact_payload` before write. Sensitive keys
(`password`, `api_key`, `token`, …) and token-like strings become `[redacted]`.
Do not store vault secrets or full Channel Shield raw payloads.

## Retention

Operator-managed SQLite file. No automatic purge in 770. Prefer short-lived
debug trajectories; export fixtures via
`keprix.trajectory.recorded.export_recorded_fixture` for recorded-session
tests (see `docs/architecture/recorded-session-tests.md`).

## Recording helpers

```python
from keprix.trajectory import get_trajectory_service

svc = get_trajectory_service()
traj = svc.create(workspace_id="default", title="debug run")
svc.record_soft_wall(traj["trajectory_id"], outcome="denied", tool_name="terminal")
svc.record_mutation(traj["trajectory_id"], stage="propose", detail={"kind": "mount"})
```

Wire Soft Wall / Mutation Engine call sites to these helpers as follow-on work;
770 delivers the store, API, UI, and contracts.

## UI

`/trajectory`: list, search filters, event list + detail, Fork, Replay (recorded).

## Non-goals

- Full time-travel debugger product
- Cordis / TypeScript rewrite
- Golden LLM quality evals (see recorded-session tests for structural CI)

## Related

- Brain session replay (`/api/brain/sessions/...`) remains graph-activation focused
- Capability seams / reversible plugins: 768, 769
- Recorded-session tests: `docs/architecture/recorded-session-tests.md` (772)
