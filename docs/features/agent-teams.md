# Agent teams

Agent teams let you compose multiple specialised agents into a coordinated crew. Each agent in a team has a defined role, a scoped tool set, and an optional MCP workbench. The team operates on a shared task under a configurable group-chat policy.

## When to use agent teams

Use a single agent for most tasks. Switch to a team when:

- The task has clearly separable sub-tasks best handled by specialists (researcher, coder, critic).
- You want a structured debate or peer review loop before committing to an answer.
- A supervisor needs to delegate and verify without doing all the work itself.

## Web UI (`/admin/teams`)

Open from **Automations > Agent Teams** in the workspace sidebar, **Settings > Agent teams**, or directly at `/admin/teams`.

This page is for **agent workflows** (YAML crews with roles and tasks), not human user onboarding. For people access, use **Settings > Workspace users** (`/settings/users`).

1. Paste or edit CrewAI-style team YAML in the editor.
2. Click **Import** to register the crew (`POST /api/teams/import`).
3. Select a team, set an objective, and **Run** (`POST /api/teams/{name}/run`).
4. Export YAML with `GET /api/teams/{name}/yaml`.

Imported teams compile into the playbook runtime (same traces and approvals as other automations).

## Group-chat policies

| Policy | Behaviour |
| --- | --- |
| `round_robin` | Each agent responds once in sequence, repeating until done |
| `supervisor` | One designated supervisor agent assigns sub-tasks to others |
| `vote` | All agents respond independently; majority rules on a decision |
| `debate` | Agents argue positions; a moderator synthesises a conclusion |
| `human_review` | Pauses after each agent reply for human comment or approval |

## MCP workbenches

Each agent in a team can have a private **MCP workbench**: a set of MCP tool bindings specific to that agent's role. For example, a security analyst agent might have access to a VirusTotal MCP server while the researcher agent only has web search.

Configure per-agent MCP bindings in the team editor under each agent's **Workbench** tab.

Dangerous MCP tools require explicit approval gating even within team runs.

## Compiling to playbooks

Team definitions can be serialised to YAML playbooks for reproducible, scheduled execution:

```bash
# From the CLI
python3 -m keprix.keprix_cli.main teams export --team-id <id> --out team.playbook.yml

# Run the saved playbook
python3 -m keprix.keprix_cli.main teams run team.playbook.yml
```

Playbooks are stored under `.keprix/multiagent/playbooks/` in the workspace.

## Running a team task

### Web UI

Enter the task objective in the **Run team task** modal. The event stream shows each agent's messages, tool calls, and handoffs.

### CLI

```bash
python3 -m keprix.keprix_cli.main teams run --team-id <id> --task "Analyse and summarise Q3 financials"
```

### API

```http
POST /api/multiagent/group-chat
Content-Type: application/json

{
  "team_id": "team-uuid",
  "message": "Analyse and summarise Q3 financials",
  "policy": "supervisor"
}
```

## API reference

| Action | Method | Endpoint |
| --- | --- | --- |
| List teams | GET | `/api/teams` |
| Create team | POST | `/api/teams` |
| Get team | GET | `/api/teams/{id}` |
| Update team | PUT | `/api/teams/{id}` |
| Delete team | DELETE | `/api/teams/{id}` |
| Run team task | POST | `/api/multiagent/group-chat` |
| Agent-to-agent messages | GET/POST | `/api/multiagent/messages` |
| Use agent as tool | POST | `/api/multiagent/agent-tools/{agent_id}/call` |
| MCP workbench tools | GET | `/api/multiagent/workbench/tools` |
| Save playbook | POST | `/api/multiagent/playbooks` |

Full schema: [REST API reference](../reference/api.md).

## Configuration

```bash
KEPRIX_MULTIAGENT_ENABLED=true
KEPRIX_MULTIAGENT_MAX_ROUNDS=30      # max conversation rounds before forced stop
KEPRIX_MULTIAGENT_TIMEOUT=600        # seconds for full team run
```

## Security note

Team runs share the same audit trail and approval requirements as single-agent runs. Each individual agent's tool calls are logged separately. Mutation proposals from within a team run are attributed to the originating agent.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Team loop does not terminate | Policy set to `round_robin` with no exit condition | Switch to `supervisor` or add a stop condition in the task description |
| Agent ignores its role | Role description too vague | Be explicit: "You are a Python security auditor. Only call security tools." |
| MCP workbench tools not appearing | MCP server not in allowlist | Add to `KEPRIX_MCP_ALLOWED_SERVERS` |
| Playbook YAML invalid on load | Schema version mismatch | Re-export from current version |

## Related

- [Agent Studio](agent-studio.md)
- [Playbooks](playbooks.md)
- [MCP integration](../integrations/mcp.md)
- [Cron jobs](cron-jobs.md)
