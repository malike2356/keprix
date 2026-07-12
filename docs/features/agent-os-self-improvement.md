# Agent OS self-improvement

Prompt **257** turns workflow audits and repeated sessions into reviewable skill
proposals.

## Flow

1. Workflow audit exports rows to `{KEPRIX_HOME}/agent-os/skill-proposals-pending.json`.
2. `/api/agent-os/skill-proposals/import` moves those rows into the proposal store.
3. `/api/agent-os/skill-proposals/scan-sessions` detects repeated real sessions.
4. Operators approve proposals at `/agent-os/skill-proposals`.
5. Approval writes a real `SKILL.md` under `{KEPRIX_HOME}/skills/{slug}/`.
6. Skill run follow-ups feed the improvement loop and weekly review report.

## API

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/agent-os/skill-proposals` | List proposals |
| POST | `/api/agent-os/skill-proposals/import` | Import prompt 256 audit queue |
| POST | `/api/agent-os/skill-proposals/scan-sessions` | Detect repeated session tasks |
| POST | `/api/agent-os/skill-proposals/{id}/approve` | Package a skill |
| POST | `/api/agent-os/skill-proposals/{id}/reject` | Reject a proposal |
| GET | `/api/agent-os/skill-review/latest` | Latest weekly report |
| PUT | `/api/agent-os/settings/self-improvement` | Save thresholds and preferences |

## Settings

Self-improvement settings live at `/settings/agent/self-improvement` and persist
under `{KEPRIX_HOME}/agent-os/self-improvement-settings.json`.
