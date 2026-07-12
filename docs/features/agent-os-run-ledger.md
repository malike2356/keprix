# Agent OS run ledger

Prompt **261** adds a unified ledger for automation runs and loop profiles for eval-backed improvement.

## What is recorded

Every ledger entry includes:

- source type and ID (`playbook`, `skill`, `agent_app`, or `cron`)
- run ID and workspace ID
- terminal status
- input and output summaries
- eval score, token count, duration, and user corrections
- creation timestamp

Playbook completions write ledger entries from the existing playbook runtime. Headless skill runs, Agent Apps, and cron-backed skills can use `record_external_run` from `keprix.agent_os.hooks`.

## Quota denials

When an actor quota blocks a run, Keprix records `quota_denied` in the security audit log and in `actor_quota_denials` (see [quotas](quotas.md)). Denial rows include `workspace_id` and optional `run_id` so operators can link the block back to the actor and workspace.

## Workspace exports

When a run belongs to a structured workspace created by prompt **258**, Keprix also writes the ledger entry to:

```text
<KEPRIX_HOME>/workspaces/<workspace>/runs/<entry_id>.json
```

The primary local store remains under:

```text
<KEPRIX_HOME>/agent-os/run-ledger/
```

The PostgreSQL migration `database/migrations/0007_agent_os_run_ledger.sql` defines the deployment table for hosted installations.

## Loop profiles

Loop profiles compare recent runs to a captured baseline. The engine currently detects:

- eval score drops greater than 10 percent
- token usage increases greater than 25 percent
- repeated user corrections
- approval backlog signals

Applying a proposal creates a draft file under:

```text
<KEPRIX_HOME>/agent-os/loop-profile-drafts/
```

Drafts are editable and never overwrite the source skill or playbook silently.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/agent-os/ledger` | List ledger entries with optional filters |
| `GET` | `/api/agent-os/ledger/{entry_id}` | Fetch one ledger entry |
| `POST` | `/api/agent-os/loop-profiles/{source}/baseline` | Capture baseline entries |
| `GET` | `/api/agent-os/loop-profiles/{source}/proposals` | Analyze drift proposals |
| `POST` | `/api/agent-os/loop-profiles/proposals/{proposal_id}/apply` | Create an editable draft |

`source` is formatted as `<source_type>:<source_id>`, for example `playbook:daily_digest`.

## UI

- `/agent-os/runs` lists ledger entries with source filters.
- `/agent-os/loop-profiles` captures baselines, analyzes drift, and creates drafts.
- Playbook run detail pages include **View in ledger**.
- Trigger builder runs (`source_type=trigger`) also appear in the ledger. See [Trigger builder](trigger-builder.md).

## Scout events

When Scout lifecycle emission is configured, Keprix emits:

- `run.completed`
- `loop.proposal.created`
