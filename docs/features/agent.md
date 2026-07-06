# Agent runtime and Mutation Engine

The Keprix agent runs an LLM-powered tool-calling loop against any configured provider. Its defining feature is the **Mutation Engine**: when the agent encounters a task no existing tool can complete, it synthesises a new Python tool, runs it inside a sandboxed environment, and presents it for your approval before installing it permanently. No code edit, no restart.

## How the agent loop works

```
User message
  -> LLM selects tool or composes reply
     -> Tool executes (built-in, MCP, or mutation-generated)
        -> Result fed back to LLM
           -> Loop until final reply or iteration limit
```

Each iteration is logged. Tool calls, results, and thinking blocks stream to the UI in real time.

## The Mutation Engine

### Capability gap detection

The agent recognises a gap when:

- No registered tool matches the required action.
- Available tools return errors the agent cannot recover from.
- The LLM explicitly requests a tool that does not exist.

### Synthesis flow

1. **Draft** - the LLM writes a self-contained Python function with typed inputs/outputs and a docstring.
2. **Sandbox** - Keprix runs the draft in an isolated Docker exec with a hard timeout (`KEPRIX_SANDBOX_TIMEOUT`, default 30 s). No host filesystem, no network egress unless declared.
3. **Approval request** - a mutation proposal is written to the database and surfaced in the configured approval channel (web UI, Telegram, Discord, etc.).
4. **Review** - you see the proposed tool name, description, code, and the task that triggered it. You accept or reject.
5. **Install** - accepted tools are written to `KEPRIX_GENERATED_TOOLS_DIR` and registered in the tool registry. Available immediately with no restart.
6. **Reuse** - the tool is available in all future agent runs on this instance.

### What a mutation looks like in the UI

Open **Workspace > Review gateway** or the `/review-gateway` route. Each pending mutation shows:

- **Trigger**: the user message that caused the gap.
- **Proposed tool**: name, docstring, and full source code.
- **Sandbox result**: stdout/stderr from the dry run.
- **Action**: Accept / Reject / Edit and re-test.

You can also receive approval requests over Telegram or Discord if `KEPRIX_MUTATION_ADMIN_CHANNEL` is set to the corresponding gateway name.

## Web UI

Open `/chat` or `/workspace` after login. The agent responds in the chat window. Mutation proposals appear as a notice inside the chat thread with a link to the review page.

When `KEPRIX_CHAT_GATEWAY_STREAM=true` (default), `/chat` routes every turn through the WEB_UI gateway stream handler. The API maps gateway events to NDJSON blocks the UI already understands:

| Gateway event | NDJSON `event` | Purpose |
| --- | --- | --- |
| `text_delta` | `text_delta` | Streaming assistant text |
| `text_done` | `text_done` | End of text for this turn |
| `tool_call` | `tool_call` | Tool started (`name`, `input`, `status`) |
| `tool_call_update` | `tool_call_update` | Tool finished (`output`, `status`) |
| `mutation` | `mutation` | Pending generated tool card |
| `error` | `error` | Recoverable stream error |

Set `KEPRIX_CHAT_GATEWAY_STREAM=false` to fall back to the legacy path (direct `stream_chat_completion` plus optional sidecar mutation bridge). Set `KEPRIX_WEB_UI_AGENT_LOOP=true` to enable the full agent tool loop in web chat when a provider is configured.

### Mutation integration (Prompt 143)

Mutation is triggered from the **agent loop tool-miss hook**, not the legacy sidecar bridge (unless `KEPRIX_CHAT_MUTATION_SIDECAR=true`). When the dispatcher reports `not_found` for a requested tool, or gap detection identifies a missing capability, `run_cycle` synthesises a tool and streams a `mutation` NDJSON event. The loop pauses until the record is approved or rejected (`KEPRIX_MUTATION_APPROVAL_TIMEOUT`, default 3600 s). After approval, the installed tool is retried automatically.

Owners review pending tools at **Workspace > Review gateway** (`/review-gateway`) or **Dashboard > Mutations** (`/dashboard/mutations`).

The admin dashboard at `/dashboard` shows pending mutations under **Mutations**.

## Configuration

Key environment variables (set in `.env`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `KEPRIX_MUTATION_ENABLED` | `true` | Master switch for the Mutation Engine |
| `KEPRIX_MUTATION_REQUIRE_APPROVAL` | `true` | Require human sign-off before installing |
| `KEPRIX_MUTATION_ADMIN_CHANNEL` | `web` | Channel for approval requests (`web`, `telegram`, `discord`) |
| `KEPRIX_GENERATED_TOOLS_DIR` | `generated_tools/` | Where installed mutations are stored |
| `KEPRIX_SANDBOX_TIMEOUT` | `30` | Seconds per sandbox run |
| `KEPRIX_MAX_TOOL_ITERATIONS` | `20` | Max tool calls per agent turn |
| `KEPRIX_CONTEXT_STRATEGY` | `summarise` | How long context is handled (`summarise` or `truncate`) |
| `KEPRIX_AGENT_DEFAULT_MODEL` | - | Override default LLM for agent runs |

## CLI

Start an interactive session:

```bash
python3 -m keprix.keprix_cli.main chat
```

Single query, non-interactive:

```bash
python3 -m keprix.keprix_cli.main -q "List all open tasks and create a summary note"
```

With specific model:

```bash
python3 -m keprix.keprix_cli.main -q "..." --model anthropic/claude-opus-4-8
```

List pending mutation proposals:

```bash
python3 -m keprix.keprix_cli.main mutations
```

Approve a mutation by ID:

```bash
python3 -m keprix.keprix_cli.main mutations approve <id>
```

## API

| Action | Method | Endpoint |
| --- | --- | --- |
| Send message (streaming) | POST | `/api/conversations/{id}/messages` |
| List mutations | GET | `/api/mutations` |
| Get mutation | GET | `/api/mutations/{id}` |
| Approve mutation | POST | `/api/mutations/{id}/approve` |
| Reject mutation | POST | `/api/mutations/{id}/reject` |
| List tools | GET | `/api/tools` |
| OpenAI-compat chat | POST | `/v1/chat/completions` |

Full schema: [REST API reference](../reference/api.md).

## Disabling the Mutation Engine

Set `KEPRIX_MUTATION_ENABLED=false` in `.env` and restart the backend. The agent will still use all built-in and MCP tools; it just will not propose new ones.

If you want mutations but not auto-approval, ensure `KEPRIX_MUTATION_REQUIRE_APPROVAL=true` (the default). Mutations are staged and do nothing until a human accepts.

## Security considerations

- Mutation code runs in an isolated container, not in the main backend process.
- Network egress from sandboxes is blocked unless a tool explicitly declares `network_hosts` and a pack admin approves.
- All mutations are logged to the audit trail.
- See [Security architecture](../security/architecture.md) and [Review gateway](../security/review-gateway.md).

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Mutations never proposed | `KEPRIX_MUTATION_ENABLED=false` | Set to `true`, restart backend |
| Sandbox always times out | Slow host, heavy operation | Increase `KEPRIX_SANDBOX_TIMEOUT` |
| Approved tool not available | Backend not restarted | Tools load dynamically; no restart needed. Check `KEPRIX_GENERATED_TOOLS_DIR` permissions |
| Cannot approve in web UI | Session expired or role | Log in as admin; mutation approval requires admin role |
| Tool installs but errors at runtime | Draft had hidden dependency | Reject and re-prompt with explicit dependency info |

## Related

- [Built-in tools](tools.md)
- [Self-coding agent](self-coding-agent.md)
- [Review gateway](../security/review-gateway.md)
- [Security architecture](../security/architecture.md)
- [MCP](../integrations/mcp.md)
