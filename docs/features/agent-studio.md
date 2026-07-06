# Agent Studio

Visual builder for multi-agent workflows, MCP bindings, and agent apps.

## Routes

| Route | Purpose |
| --- | --- |
| `/agent-studio` | Role graph, connections, group chat policy, dry-run |
| `/agent-apps` | Manifest-driven app runners (CLI, web, API) |
| `/agent-runtime` | Live run console and streams |

## Multi-agent runtime

- Agent-to-agent messaging with tool and approval message types
- `GroupChat` policies: round robin, supervisor, vote, debate, human review
- `McpWorkbench` for MCP tool listing, binding, and approval gating
- Playbook YAML save/load under `.keprix/multiagent/playbooks/`

## API

| Action | Endpoint |
| --- | --- |
| Messages | `GET/POST /api/multiagent/messages` |
| Agent as tool | `POST /api/multiagent/agent-tools/{agent_id}/call` |
| Group chat | `POST /api/multiagent/group-chat` |
| MCP workbench | `GET /api/multiagent/workbench/tools` |
| Playbooks | `POST /api/multiagent/playbooks` |

## Agent apps

Manifest-driven folders with bundled eval suites and per-run trace capture.

- Install and run portable apps at `/agent-apps` ([Agent Apps guide](agent-apps.md))
- Export zip bundles from the hub or CLI `keprix agent-app bundle`
- Agent Studio graphs can publish compatible bundles; see [Agent Apps](agent-apps.md#export-from-agent-studio)

## Policies

Studio runs use vault, approval, and trace primitives. Dangerous MCP tools require explicit approval.

## Related

- [Playbooks](playbooks.md)
- [MCP](../integrations/mcp.md)
- [Agent Apps](agent-apps.md)
