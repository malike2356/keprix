# Agent runtime

The agent runtime is the engine that processes each conversational turn: it runs the agent loop, dispatches tool calls, manages context, and enforces safety gates. Understanding the runtime helps you configure it correctly and diagnose unexpected behaviour.

## Agent loop

A single turn runs the following loop:

```
1. Build context
   - Retrieve relevant memory (ChromaDB search, recent messages)
   - Attach project goal and active tools
   - Apply active persona (SAGE / FORGE / WARDEN / COMPASS)

2. LLM call
   - Send messages + tool manifest to the configured provider
   - Stream the response

3. Dispatch tool calls
   - Parse tool call from the response
   - Validate inputs against the tool manifest
   - Execute the tool (built-in, pack, or mutation-generated)
   - Append tool result to context

4. Repeat from step 2 until:
   - No further tool calls (terminal response)
   - Iteration limit reached (KEPRIX_AGENT_MAX_ITERATIONS)
   - Safety gate triggered (requires human approval)
   - User interrupts
```

The loop is fully streamed: each token and tool event is sent to the client as an SSE event.

## Context window management

The runtime uses a context budget to fit the conversation history and retrieved context within the model's context limit:

- Recent messages: always included in full.
- Older messages: summarised automatically if the window is approaching capacity.
- Retrieved memory: top-k results by relevance score, truncated if needed.
- Project files: included by explicit reference; the agent asks for files it needs.
- Tool manifests: compact mode strips descriptions when the window is tight.

Configure the context budget:

```bash
KEPRIX_CONTEXT_BUDGET_TOKENS=100000    # max tokens to send per turn (default: model context - 10k)
KEPRIX_MEMORY_TOP_K=8                  # memory documents to retrieve per turn
KEPRIX_SUMMARISE_HISTORY_AT=0.8        # summarise when context is 80% full
```

## Iteration limit

```bash
KEPRIX_AGENT_MAX_ITERATIONS=20         # default: 20 tool-call rounds per turn
```

If the agent reaches the iteration limit before producing a terminal response, the runtime stops and returns a partial response with a warning. Increase this for complex playbook steps, but watch for runaway loops.

## Personas

Personas shape the system prompt, available tools, and safety gates applied to a turn. The active persona is set by the workspace route:

| Persona | Route | Character |
| --- | --- | --- |
| SAGE | `/chat` | General assistant, all tools |
| FORGE | `/coding` | Code and engineering focus, coding tools only |
| WARDEN | `/security` | Security and audit tasks, security packs |
| COMPASS | `/research`, `/opportunity` | Research and analysis, no code execution |

Personas are defined in `keprix/keprix_agent/personas/`. You can override the system prompt per-conversation using the API:

```http
POST /api/conversations
{
  "persona": "FORGE",
  "system_prompt_override": "You are working on a TypeScript project. Prefer functional patterns."
}
```

## Tool dispatch

The runtime supports three tool sources:

1. **Built-in tools** (`keprix/keprix_agent/tools/`): always available, maintained by the project.
2. **Pack tools**: installed via the Hub or API; available when the pack is active.
3. **Mutation tools**: synthesised by the agent and approved by the user; stored in `keprix/mutations/`.

Tool calls are validated against the manifest before execution. If inputs are invalid, the runtime returns a validation error to the model rather than raising an exception.

## Safety gates

The runtime has two safety gate levels:

| Gate level | Trigger | Behaviour |
| --- | --- | --- |
| `warn` | Tool flagged as medium risk | Logs to audit log; proceeds |
| `require_approval` | Tool flagged as high risk or mutation being installed | Pauses the loop, notifies user, waits for approval |

Risk level is set in the tool manifest. Mutation proposals always require approval. You can also flag specific tool inputs as triggering approval (e.g., `delete_file` with irreversible paths).

Configure per-tool gate overrides in **Admin > Settings > Tool gates**.

## Event stream

Every runtime event is emitted as a server-sent event:

| Event type | Payload |
| --- | --- |
| `content` | `{delta: string}` - a token from the LLM |
| `tool_call` | `{id, name, inputs}` - about to call a tool |
| `tool_result` | `{id, output, status}` - tool returned |
| `thinking` | `{delta}` - extended thinking token (if enabled) |
| `approval_required` | `{tool, reason}` - safety gate paused |
| `done` | `{usage: {input_tokens, output_tokens}}` |
| `error` | `{code, message}` |

Subscribe to the stream:

```bash
curl -N http://localhost:3333/api/conversations/{id}/stream \
  -H "Authorization: Bearer $KEPRIX_API_KEY"
```

## Extended thinking

Some providers (Anthropic extended thinking, DeepSeek R1) return explicit reasoning tokens. Enable display in settings:

```bash
KEPRIX_SHOW_THINKING=true    # stream thinking tokens to the UI
```

Thinking tokens count toward context and billing.

## Configuring the runtime

All env vars use the `KEPRIX_` prefix:

```bash
KEPRIX_AGENT_MAX_ITERATIONS=20
KEPRIX_CONTEXT_BUDGET_TOKENS=100000
KEPRIX_MEMORY_TOP_K=8
KEPRIX_SUMMARISE_HISTORY_AT=0.8
KEPRIX_SHOW_THINKING=false
KEPRIX_SANDBOX_TIMEOUT=30
```

See [Environment variables](../configuration/environment-variables.md) for the full list.

## Related

- [Agent and Mutation Engine](agent.md)
- [Tools](tools.md)
- [Memory and RAG](memory.md)
- [Evals and observability](evals.md)
- [Security architecture](../security/architecture.md)
