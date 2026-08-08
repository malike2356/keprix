# Prompt: Adopt Resource-Scoped Tool ACLs For Keprix

## Goal

Make Keprix tool and connector permissions resource-specific so agents can be trusted with narrow access instead of broad service access.

## Source Research

Reference only:

- `/opt/lampp/htdocs/verlox/keprix/1st-plan/competitor-research/00-agents-to-adopt/myapi-open/src/lib/service-resource-scopes.js`
- `/opt/lampp/htdocs/verlox/keprix/1st-plan/competitor-research/00-agents-to-adopt/myapi-open/SERVICE_CATALOG.md`

Do not copy AGPL code. Reimplement the behavior.

## Required Behavior

- Extend Keprix tool ACLs with resource IDs and action classes.
- Example resources: GitHub repository, local workspace path, MCP server, Slack channel, Notion page, Google Drive folder, calendar, database table, hosted app, deployment target.
- Extract target resource from command args, tool call input, connector metadata, request path, body, or query.
- Fail closed for write, deploy, delete, mutation, repo edit, and external side-effect actions when the resource cannot be determined.
- Keep read-only resource checks less restrictive where product policy allows.
- Add UI and CLI controls to approve exact resources for each agent or token.
- Log resource-scope violations with actor, tool, action, target, workspace, and policy decision.

## Implementation Targets To Inspect

- `src`
- `web`
- `docs/features/tools.md`
- `docs/features/mcp-connector-first.md`
- `docs/features/agent-os-workflow-audit.md`
- `docs/features/self-coding-agent.md`
- Existing governance, tool registry, run ledger, and approval modules.

## Implementation Steps

1. Inventory all Keprix tools and connectors by side-effect risk.
2. Define a resource descriptor format.
3. Add per-tool resource extraction helpers.
4. Add policy checks before tool execution.
5. Add approval controls in settings and agent configuration.
6. Add migration behavior for existing broad grants.
7. Update run ledger and audit views to show resource decisions.
8. Update docs and self-knowledge so Keprix can explain its own ACL model.

## Tests

- Approved resource action succeeds.
- Unapproved resource action is denied.
- Indeterminate write target is denied.
- Read and write policies differ where intended.
- Existing broad grants remain visible and can be narrowed.

## Done Criteria

- Agent tool access can be scoped to exact resources.
- Dangerous actions fail closed.
- Users can understand and edit grants.
- Audit logs explain resource policy decisions.
- No AGPL code is copied.
