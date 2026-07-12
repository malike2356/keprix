# Agent OS promotion

Prompt **260** adds the promotion ladder from approved skill to automation.

## Targets

| Target | Created artifact |
| --- | --- |
| Cron job | Existing Keprix cron job with the skill loaded |
| Playbook | YAML playbook under `{KEPRIX_HOME}/playbooks/promoted/` |
| Agent App | Installable app folder under `{KEPRIX_HOME}/agent-apps/` |

Links are stored in `{KEPRIX_HOME}/agent-os/automation-links.json`.

## API

| Method | Route | Purpose |
| --- | --- | --- |
| POST | `/api/agent-os/promote` | Promote skill to `cron`, `playbook`, or `agent_app` |
| GET | `/api/agent-os/links?skill=...` | List linked automations |
| DELETE | `/api/agent-os/links/{type}/{id}` | Remove link without deleting the skill |

## CLI

```bash
keprix agent-os promote --skill daily-brief --to cron --schedule "0 8 * * 1-5"
keprix agent-os promote --skill research-brief --to agent-app
keprix agent-os links --skill daily-brief
```
