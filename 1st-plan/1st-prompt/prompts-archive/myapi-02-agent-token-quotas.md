# Prompt: Adopt Agent And Token Quotas For Keprix

## Goal

Give Keprix clear quotas for agents, API tokens, workspaces, generated tools, automations, and model usage.

## Source Research

Reference only:

- `/opt/lampp/htdocs/verlox/keprix/1st-plan/competitor-research/00-agents-to-adopt/myapi-open/src/lib/agent-limits.js`
- `/opt/lampp/htdocs/verlox/keprix/1st-plan/competitor-research/00-agents-to-adopt/myapi-open/src/tests/agent-limits.test.js`

Do not copy AGPL code. Reimplement the behavior.

## Required Behavior

- Support quotas by day and month.
- Support max calls, max estimated tokens, max tool runs, max mutation runs, and per-service limits.
- Scope quotas to workspace, agent, API token, user, and edition.
- Return 429 or local equivalent when limits are exceeded.
- Expose remaining quota in API responses and the web UI.
- Record quota denials in audit logs.
- Keep quotas separate from billing credits.
- Apply stricter defaults to trials and public-hosted accounts than local self-hosted installs.

## Implementation Targets To Inspect

- `src`
- `web`
- `docs/features/agent-runtime.md`
- `docs/features/tools.md`
- `docs/features/self-coding-agent.md`
- `docs/features/agent-os-run-ledger.md`
- Current auth, token, workspace, and run-ledger modules.

## Implementation Steps

1. Inventory expensive or abuse-prone actions.
2. Define a quota policy schema compatible with existing config style.
3. Add a counter store keyed by workspace, actor, service, and period.
4. Add enforcement before model calls, tool runs, generated-tool execution, repo-edit jobs, and automations.
5. Add UI and CLI surfaces for current quota and remaining allowance.
6. Add admin controls for overrides.
7. Add run-ledger links from quota denials back to the actor and workspace.

## Tests

- Quota allows calls below limit.
- Quota blocks calls at limit.
- Agent A cannot consume Agent B allowance.
- API token quota is isolated from user quota.
- Daily and monthly windows reset correctly.
- Denials are audited.

## Done Criteria

- Keprix has predictable cost and abuse controls.
- Hosted plans can safely expose generated tools and self-coding.
- Operators can explain why a run was denied.
- No AGPL code is copied.
