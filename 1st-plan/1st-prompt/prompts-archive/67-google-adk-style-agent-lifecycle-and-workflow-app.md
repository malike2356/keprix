# keprix - Prompt 67: Google ADK-Style Agent Lifecycle and Workflow App

> **Status (2026-07-05):** Implemented under `src/keprix/agent_apps/` with sample `hello-agent`, CLI (`keprix agent-app`), API routes, web UI at `/agent-apps`, lifecycle traces, eval runner, and deployment bundles. 8 tests in `tests/agent_apps/`.

## Context

Adopt Google ADK's useful concepts: agent folders, local CLI runner, web UI runner, graph workflows, lifecycle events, tool definitions, evals, and deployable agent packages.

This extends Prompts 31, 39, 41, 64, and 65.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/google-adk-python/README.md
planning/agents-to-adopt/google-adk-python/src/google/adk
```

## Files To Create Or Extend

```text
backend/agent_apps/
  __init__.py
  app_manifest.py
  lifecycle.py
  local_runner.py
  web_runner.py
  deployment_bundle.py
  eval_runner.py
cli/commands/agent_app.py
frontend/src/app/agent-apps/page.tsx
frontend/src/components/agent-apps/AgentAppList.tsx
frontend/src/components/agent-apps/AgentAppRunner.tsx
tests/agent_apps/test_manifest.py
tests/agent_apps/test_lifecycle.py
tests/agent_apps/test_local_runner.py
```

## Required Features

### Agent App Manifest

Define a portable app folder:

```text
agent.yaml
instructions.md
tools/
playbooks/
evals/
README.md
```

Manifest includes:

- Name.
- Version.
- Agent entrypoint.
- Tools.
- Playbooks.
- Required env keys.
- Required permissions.
- Eval suite.

### Lifecycle Events

Support hooks:

- Before run.
- After run.
- Before tool.
- After tool.
- On error.
- On approval requested.
- On artifact created.

### Runners

Provide:

- CLI runner.
- Web UI runner.
- API runner.
- Scheduled runner.

### Deployment Bundle

Package an agent app for:

- Local install.
- Hub submission.
- Docker deployment.
- Workspace import.

## Acceptance Criteria

- A sample agent app runs from CLI and web UI.
- Lifecycle hooks emit traces.
- App manifests are validated before install.
- Eval runner can run the app's bundled tests.
- Deployment bundle excludes secrets and local cache.

