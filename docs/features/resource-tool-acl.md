# Resource-scoped tool ACL

Keprix can limit agents and API tokens to **exact resources** instead of whole services.

Product tool-name ACL (`ToolACL`) still decides whether a tool name is allowed.
Resource ACL decides whether the **target** (repo, path, channel, calendar, table, deploy target, and so on) is approved.

## Model

| Layer | Question |
| --- | --- |
| Product ACL | Is this tool name allowed for the product? |
| Resource ACL | Is this resource ID allowed for the actor? |

Empty resource grants for a service mean **unrestricted** (legacy broad access). Once you approve one or more IDs for a kind, only those IDs are allowed.

## Action classes

- `read`: less restrictive when the target ID cannot be determined
- `write`, `delete`, `deploy`, `mutate`, `side_effect`: **fail closed** if the target cannot be determined

## Services and kinds

See `GET /api/security/acl/resources/catalog`. Includes GitHub repos, filesystem paths (prefix match), MCP servers, Slack channels, Notion pages, Drive folders, calendars, database tables, deploy targets, mutation workspaces, and hosted apps.

## API

| Method | Path |
| --- | --- |
| GET | `/api/security/acl/resources/catalog` |
| GET | `/api/security/acl/resources/grants?actor_type=&actor_id=` |
| PUT | `/api/security/acl/resources/grants` |
| DELETE | `/api/security/acl/resources/grants` |
| POST | `/api/security/acl/resources/check` |
| POST | `/api/security/acl/resources/broad` |
| GET | `/api/security/acl/audit` |

## Runtime

`tool_executor` calls `evaluate_tool_acl_gate` before dispatch (sequential and concurrent). Denials return a structured `[tool_acl_denied]` tool result and are audited with actor, tool, action, target, workspace, and policy decision.

## UI

Admin **Tool ACL** (`/admin/tool-acl`) is the operator console for product ACL
snapshots, resource grants, check playground, and audit. Do not confuse it with
**Generated tools** (`/admin/tools`), which only reviews mutation-engine tools.

See [Tool ACL](tool-acl.md).

## Migration

Existing broad service access stays available until you add exact grants. Use `POST /resources/broad` to record a visible legacy broad grant while you narrow it.
