# keprix - Prompt 61: OpenHands-Style Agent Control Center

## Context

Adopt OpenHands' strongest product idea into keprix: a self-hosted control center for long-running software agents, multiple agent servers, scheduled automation, event-triggered work, and team-visible engineering activity.

Do not copy OpenHands UI text or architecture wholesale. Rebuild the behavior in keprix's own app shell.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/openhands/README.md
planning/agents-to-adopt/openhands/openhands
planning/agents-to-adopt/openhands/openhands-ui
```

## Files To Create

```text
backend/control_center/
  __init__.py
  agent_server_registry.py
  automation_server.py
  event_triggers.py
  scheduled_runs.py
  workspace_sessions.py
  run_queue.py
  activity_feed.py
  remote_agent_client.py
frontend/src/app/control-center/page.tsx
frontend/src/components/control-center/AgentServerList.tsx
frontend/src/components/control-center/AutomationRules.tsx
frontend/src/components/control-center/RunQueue.tsx
frontend/src/components/control-center/ActivityFeed.tsx
tests/control_center/test_agent_server_registry.py
tests/control_center/test_event_triggers.py
tests/control_center/test_scheduled_runs.py
```

## Required Features

### Agent Server Registry

Allow keprix to manage multiple local or remote agent servers:

- Name.
- URL.
- Health status.
- Capabilities.
- Workspace root.
- Sandbox status.
- Last heartbeat.
- Owner.

### Agent Sessions

Create, pause, resume, and stop long-running sessions:

- Coding task.
- Research task.
- Browser task.
- Analytics task.
- Opportunity task.
- Custom playbook.

Every session must write trace events and artifacts.

### Automation Server

Support automations triggered by:

- Schedule.
- Webhook.
- GitHub issue.
- Pull request event.
- New file in workspace.
- New email or channel message.
- Manual button.

### Control Center UI

Build a single operator page showing:

- Connected agent servers.
- Active sessions.
- Queued work.
- Failed runs.
- Scheduled automations.
- Recent artifacts.
- Human approval requests.

## Security Requirements

- Remote agent servers require explicit registration.
- Tokens are stored in the vault.
- Destructive tasks require approval.
- Workspace paths must be allowlisted.
- Webhook triggers require signature verification.

## Acceptance Criteria

- A user can register a local keprix agent server.
- A user can schedule a playbook run.
- A user can trigger a run from a webhook.
- UI shows active and completed runs.
- Failed runs expose logs without leaking secrets.
- No OpenHands branding appears in shipped UI.

