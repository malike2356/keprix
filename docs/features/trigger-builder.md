# Trigger builder

Unify playbooks, schedules, and event automations behind a single **When this, do that** builder. Users do not need to edit cron config for common cases.

## Concepts

| Piece | Meaning |
| --- | --- |
| Trigger | Named automation with schedule or event ingress |
| Action | `run_playbook`, `ask_agent`, `call_tool`, `run_mutation`, `create_task`, `call_webhook`, `request_approval` |
| Run | Queued execution with lease lock, history, cost/quota fields, optional approval |
| AI mode | `managed` (wallet) or `byok` |

## Schedules

Structured schedules (UI-friendly):

- `interval` (`every_minutes`)
- `daily` / `weekly` / `monthly` (hour + minute)
- `cron` (advanced escape hatch)
- `once` (ISO timestamp; disables after fire)

Timezone is stored per trigger (default UTC).

## Events

Event sources: `connector`, `webhook`, `run_ledger`, `repository`, `workspace`, `manual`.

Ingress: `POST /api/triggers/events` with `{ source, event_type, payload }`.

## Safety

- Risky actions (`call_tool`, `run_mutation`, `call_webhook`) wait for approval when `approval_mode=auto` (or always when `required`).
- Worker claims use a lease so concurrent workers do not double-run.
- LLM-backed actions check actor quotas and managed wallet (or skip wallet when `ai_mode=byok`).
- Tool actions consult product tool ACL.
- Completions write Agent OS run-ledger entries (`source_type=trigger`).

## UI

Open **Automations > Triggers** (`/playbooks/triggers`):

- Create schedule triggers
- Test run, pause/resume
- Approve awaiting runs
- View history and ledger ids

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET/POST` | `/api/triggers` | List / create |
| `GET/PATCH/DELETE` | `/api/triggers/{id}` | Read / update / delete |
| `POST` | `/api/triggers/{id}/test` | Enqueue + process one test run |
| `GET` | `/api/triggers/{id}/runs` | History for one trigger |
| `GET` | `/api/triggers/runs` | Recent runs |
| `POST` | `/api/triggers/runs/{id}/approve` | Resume awaiting approval |
| `POST` | `/api/triggers/events` | Event ingress |
| `POST` | `/api/triggers/tick` | Schedule tick + process queue |

Background ticker runs in the API lifespan when `KEPRIX_TRIGGER_ENGINE_ENABLED` is not off (interval `KEPRIX_TRIGGER_TICK_SEC`, default 30s).

## Related

- [Playbooks](playbooks.md)
- [Cron jobs](cron-jobs.md) (low-level schedule escape hatch)
- [Agent OS action board](agent-os-action-board.md)
- [Agent OS run ledger](agent-os-run-ledger.md)
- [Control Center](../reference/api.md) (legacy webhook/schedule automations still available)
