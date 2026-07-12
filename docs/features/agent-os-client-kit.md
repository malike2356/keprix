# Agent OS client kit

Prompt **263** adds a handoff bundle and simplified recipient experience.

## Client kit export

The export creates a zip with:

- `manifest.json`
- `action-board.json`
- `automations/cron/*.json`
- `automations/playbooks/*.yaml`
- `automations/agent-apps/*/agent.yaml`
- `workspace-template/template.json`
- `KEPRIX.md`
- `SECRETS_CHECKLIST.md`
- `SETUP.md`

Secret values are never exported. The checklist contains only referenced key names such as `OPENAI_API_KEY`.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/agent-os/client-kit/preview` | Preview exported pins, automations, and secret key names |
| `POST` | `/api/agent-os/client-kit/export` | Build and download a kit zip |
| `POST` | `/api/agent-os/client-kit/import` | Import a kit zip; admin only |
| `GET` | `/api/agent-os/simplified-mode` | Read simplified-mode settings |
| `PUT` | `/api/agent-os/simplified-mode` | Update simplified mode; admin only |
| `GET` | `/api/agent-os/simplified-mode/guard?path=...` | Check whether a path should redirect |

## UI

Open `/settings/agent-os/client-kit` to preview, export, import, and enable simplified mode.

## Simplified mode

Simplified mode keeps the recipient focused on:

- `/agent-os`
- Agent Apps
- Chat
- Documents

Advanced routes such as Agent Studio, playbook studio, coding, MCP, browser automation, and control center are hidden from navigation for non-admin roles. Admins and owners keep the full curated nav. Direct visits in the web app redirect to `/agent-os` when the guard applies. See [Navigation and roles](navigation-and-roles.md).

## Security

Remote kit and agent clients that use API keys are subject to first-seen client approval on hosted deployments. See [Client approval and token security](client-approval-token-security.md).
