# Agent OS Action Board

Prompt **262** adds `/agent-os`, a headless action surface for pinned skills, promoted playbooks, and Agent Apps.

## What it does

- Pins actions per user in `{KEPRIX_HOME}/agent-os/action-board.json`
- Runs actions without opening a chat tab
- Shows progress/result details and a ledger link
- Captures 24-hour metrics from the run ledger
- Schedules skill pins through the prompt **260** promoter
- Adds command palette entries for pinned actions
- Runs page-level keyboard shortcuts such as `Ctrl+Shift+B`

## Headless run API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/agent-os/run/skill/{slug}` | Run a skill headlessly |
| `POST` | `/api/agent-os/run/playbook/{id}` | Run a promoted playbook |
| `POST` | `/api/agent-os/run/agent-app/{name}` | Run an Agent App |
| `GET` | `/api/agent-os/run/{run_id}/status` | Fetch progress and result |

Each terminal run writes to the prompt **261** ledger.

## Board API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/agent-os/board` | Load board config, actions, links, and metrics |
| `PUT` | `/api/agent-os/board` | Replace pins |
| `POST` | `/api/agent-os/board/pins` | Pin an action |
| `DELETE` | `/api/agent-os/board/pins/{pin_id}` | Remove a pin |
| `POST` | `/api/agent-os/board/schedule` | Promote a skill pin to cron |

## Metrics

The metrics row uses ledger data:

- token burn in the last 24 hours
- runs today
- failed runs
- pending approval backlog

## UI

Open `/agent-os` to run pinned actions, search all actions, schedule skill pins, and inspect the latest result. The launcher and navigation now include **Agent OS**.

For schedule and event automations without raw cron config, use the [Trigger builder](trigger-builder.md) (`/playbooks/triggers`).
