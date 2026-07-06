# Playbooks

Playbooks are YAML-defined automation workflows. A playbook is a directed graph of steps: each step runs an agent task, calls an API, or makes a decision. Playbooks support conditional edges, checkpointing (resume after failure), and human approval interrupts for risky steps.

!!! note "Playbooks vs Local models"
    **Playbooks** (`/playbooks`) are automation graphs. The similarly named **Playbook** route (`/playbook`) manages local Ollama models. See [Local models](local-models.md).

## When to use playbooks

Use playbooks when:

- You need a repeatable multi-step workflow (daily digest, incident response, report generation).
- A workflow must survive failures and resume from the last successful step.
- Some steps require human review before proceeding.
- You want to schedule a workflow on a cron schedule.

For one-off tasks, use chat. For purely scheduled single-step tasks, use [Cron jobs](cron-jobs.md).

## Anatomy of a playbook

```yaml
# .keprix/playbooks/daily-digest.yml
id: daily-digest
name: Daily digest
description: Reads email, tasks, and calendar then posts a summary note

steps:
  - id: fetch_emails
    type: agent_task
    prompt: "List the 5 most important unread emails in my inbox"
    tools: [email_list, email_read]
    output_key: emails

  - id: fetch_tasks
    type: agent_task
    prompt: "List all in-progress tasks"
    tools: [list_tasks]
    output_key: tasks

  - id: fetch_calendar
    type: agent_task
    prompt: "List today's calendar events"
    tools: [calendar_list]
    output_key: calendar

  - id: write_summary
    type: agent_task
    prompt: |
      Write a concise daily digest from the following data.
      Emails: {{ steps.fetch_emails.output }}
      Tasks: {{ steps.fetch_tasks.output }}
      Calendar: {{ steps.fetch_calendar.output }}
    tools: [create_note]
    output_key: summary

edges:
  - from: fetch_emails
    to: write_summary
  - from: fetch_tasks
    to: write_summary
  - from: fetch_calendar
    to: write_summary
```

Steps referencing each other's `output_key` create implicit dependencies. The runtime runs independent steps in parallel.

## Step types

| Type | What it does |
| --- | --- |
| `agent_task` | Runs a prompt through the agent with a scoped tool set |
| `http` | Calls an external HTTP endpoint |
| `condition` | Evaluates an expression and routes to different next steps |
| `human_approval` | Pauses execution and waits for user input |
| `playbook` | Runs a child playbook (nesting up to 3 levels) |
| `code` | Runs a Python snippet in sandbox |
| `wait` | Delays for a fixed duration or until a condition is met |

### Human approval step

```yaml
  - id: approve_send
    type: human_approval
    message: "Ready to send the weekly report email. Approve?"
    channel: web          # web, telegram, discord
    timeout_hours: 24
    on_timeout: reject    # or 'approve' for unattended pipelines
```

If `channel: telegram`, the approval request is sent as a Telegram message with Accept/Reject inline buttons.

### Condition step

```yaml
  - id: check_urgency
    type: condition
    expression: "steps.triage.output.urgency == 'high'"
    on_true: escalate
    on_false: log_only
```

## Web UI (`/playbooks`)

- **Playbook list**: all saved playbooks with last-run status.
- **New playbook**: YAML editor with syntax highlighting and schema validation.
- **Run history**: per-run event streams, step status, and output values.
- **Resume**: failed runs can be resumed from the last successful checkpoint.

## Saving a playbook

Drop a YAML file into `.keprix/playbooks/` on the server, or create one in the UI. The runtime picks it up immediately.

Via API:

```http
POST /api/playbooks
Content-Type: application/json

{
  "name": "daily-digest",
  "yaml": "..."
}
```

## Running a playbook

### Web UI

Click **Run** next to a playbook in the list.

### CLI

```bash
python3 -m keprix.keprix_cli.main playbooks run daily-digest
python3 -m keprix.keprix_cli.main playbooks run daily-digest --input date=2026-07-06
```

### API

```http
POST /api/playbook-runs/start
{"playbook_id": "daily-digest", "inputs": {"date": "2026-07-06"}}
```

### Via cron

Schedule a playbook in **Admin > Cron** by selecting it as the job target. See [Cron jobs](cron-jobs.md).

## Monitoring a run

```http
GET /api/playbook-runs/{run_id}
GET /api/playbook-runs/{run_id}/events    # Server-sent events stream
```

Events include step start, step complete, step failed, approval requested, approval received.

## Resuming after failure

Playbooks checkpoint after each completed step. If a run fails mid-way, resume from the last checkpoint:

```http
POST /api/playbook-runs/{run_id}/resume
```

Or in the UI: find the failed run, click **Resume**.

## Checkpointing and idempotency

Steps marked `idempotent: true` can safely be re-run on resume:

```yaml
  - id: send_notification
    type: agent_task
    idempotent: false    # do not re-run on resume (would send notification again)
    prompt: "Send the digest summary as a Slack message"
```

Non-idempotent steps are skipped on resume unless explicitly requested.

## API

| Action | Method | Endpoint |
| --- | --- | --- |
| List playbooks | GET | `/api/playbooks` |
| Create / update | POST | `/api/playbooks` |
| Get playbook | GET | `/api/playbooks/{id}` |
| Delete | DELETE | `/api/playbooks/{id}` |
| Start run | POST | `/api/playbook-runs/start` |
| Get run | GET | `/api/playbook-runs/{run_id}` |
| Resume run | POST | `/api/playbook-runs/{run_id}/resume` |
| Event stream | GET | `/api/playbook-runs/{run_id}/events` |
| List runs | GET | `/api/playbook-runs` |

## Integrations

- **CrewAI**: CrewAI flows export to Keprix playbook YAML via the team export command.
- **RAG pipelines**: long-running RAG jobs register a `playbook_run_id` for correlation.
- **Agent personas**: SAGE, FORGE, WARDEN, and COMPASS personas compile their briefs through playbook graphs.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Run stuck at approval step | Approver did not act, timeout not set | Set `timeout_hours` and `on_timeout` |
| Steps run out of order | Missing edge declaration | Add explicit `edges` between steps |
| Template variable `{{ steps.x.output }}` empty | Step x ran after referencing step | Add edge from x to the referencing step |
| Resume re-runs completed steps | Step marked `idempotent: true` but run re-started | Mark idempotent steps correctly; use `POST /resume` not `POST /start` |

## Related

- [Cron jobs](cron-jobs.md)
- [Agent teams](agent-teams.md)
- [Agent Studio](agent-studio.md)
- [Evals](evals.md)
