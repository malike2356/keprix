# Built-in tools

Tools are Python-callable capabilities registered in the agent's tool registry. On each turn the LLM selects which tools to call, calls them in sequence, and feeds results back until the task is complete or the iteration limit is reached.

## Tool categories

| Category | Examples |
| --- | --- |
| Filesystem | Read file, write file, list directory, search files |
| Web | Search (SearXNG), fetch URL, extract page content |
| Workspace | Create task, add note, send email draft, calendar event |
| Code execution | Run Python snippet in sandbox, run shell command |
| Data | Parse CSV, query JSON, convert formats |
| Memory | Store memory, recall memory, search embeddings |
| System | Health check, environment info, list tools |
| MCP | Any tool from connected MCP servers |
| Mutation-generated | Tools synthesised and approved by the instance owner |

## Viewing installed tools

### Web UI

Go to **Admin > Tools** (`/admin/tools`). The table lists every registered tool with its name, source (built-in, MCP, or generated), description, and enabled/disabled toggle.

### CLI

```bash
python3 -m keprix.keprix_cli.main tools
python3 -m keprix.keprix_cli.main --list_tools
```

### API

```http
GET /api/tools
```

Returns the full tool manifest including name, description, parameter schema, and source.

## Enabling and disabling tools

Tools can be toggled globally in **Admin > Tools** or per-session in chat settings. Disabled tools are excluded from the context sent to the LLM.

Dangerous tools (network calls, file writes, system commands) are tagged with a risk level. High-risk tools require explicit confirmation unless `KEPRIX_AUTO_APPROVE_HIGH_RISK=true` is set (not recommended for shared instances).

## Toolsets

Toolsets are named subsets for focused agent runs:

```bash
# CLI: restrict to web and terminal tools only
python3 -m keprix.keprix_cli.main chat -t web,terminal
```

Pre-defined sets: `web`, `terminal`, `workspace`, `data`, `code`, `minimal`. Custom sets can be saved in **Admin > Tools > Toolsets**.

## Mutation-generated tools

When the Mutation Engine produces an approved tool it is written to `KEPRIX_GENERATED_TOOLS_DIR` (default `generated_tools/`) and registered automatically. These tools appear in the tool list with source `mutation`.

To review, edit, or remove a generated tool:

1. Open **Admin > Mutations** or `/dashboard/mutations`.
2. Find the installed mutation, click **View source**.
3. Edit inline or click **Revoke** to uninstall.

See [Agent runtime and Mutation Engine](agent.md) for the full synthesis flow.

## MCP tools

Tools from MCP (Model Context Protocol) servers are listed alongside built-ins. Configure MCP servers in **Developer > MCP** or via environment:

```bash
KEPRIX_MCP_ALLOWED_SERVERS=filesystem,github,postgres
```

See [MCP integration](../integrations/mcp.md).

## Writing a custom tool manually

A tool is a Python file that exports a `@tool` decorated function:

```python
from keprix.tools.registry import tool

@tool(name="send_slack_message", description="Post a message to a Slack channel")
def send_slack_message(channel: str, text: str) -> dict:
    """
    channel: Slack channel ID or name
    text: Message body
    """
    import httpx
    token = os.environ["SLACK_BOT_TOKEN"]
    r = httpx.post("https://slack.com/api/chat.postMessage",
                   json={"channel": channel, "text": text},
                   headers={"Authorization": f"Bearer {token}"})
    return r.json()
```

Drop the file in `KEPRIX_GENERATED_TOOLS_DIR` or in `keprix/tools/custom/`. It will be picked up on the next startup (or immediately if hot-reload is enabled).

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `KEPRIX_GENERATED_TOOLS_DIR` | `generated_tools/` | Directory for mutation-installed tools |
| `KEPRIX_MAX_TOOL_ITERATIONS` | `20` | Max tool calls per agent turn |
| `KEPRIX_AUTO_APPROVE_HIGH_RISK` | `false` | Skip confirmation for risky tools |
| `KEPRIX_TOOL_TIMEOUT` | `60` | Seconds before a tool call is killed |
| `KEPRIX_MCP_ALLOWED_SERVERS` | _(empty)_ | Comma-separated allowlist of MCP servers |

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Tool not appearing in chat | Disabled or not in current toolset | Toggle in Admin > Tools |
| Tool errors every time | Missing env var or dependency | Check tool source; add env var to `.env` |
| Agent calls tool in loop | Tool returns unexpected output format | Check tool docstring; add output schema |
| MCP tools not listed | MCP server not in allowlist or not running | Check `KEPRIX_MCP_ALLOWED_SERVERS` and server logs |

## Related

- [Agent runtime and Mutation Engine](agent.md)
- [Self-coding agent](self-coding-agent.md)
- [MCP integration](../integrations/mcp.md)
- [Review gateway](../security/review-gateway.md)
