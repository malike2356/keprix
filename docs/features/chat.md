# Chat

The chat workspace is the primary interface to your local Keprix agent. It supports multi-turn conversations, tool use, model switching, and slash commands.

## Open chat

- Route: `/chat`
- Launcher card: **Chat**
- Sidebar: **Workspace > Chat**

Starting a **New conversation** creates a session immediately; the UI does not redirect you into an old thread.

## Layout

| Region | Purpose |
| --- | --- |
| Session list | Past conversations, rename, delete, star |
| Message feed | User and agent messages, tool calls, code blocks |
| Input bar | Text input, model selector, attachments; [web voice input](web-voice-input.md) (mic, prompts 188-191) planned |
| Header nav | **Home** (`/launcher`) and **Dashboard** (`/dashboard`, admins only) |

## Models

Use the model selector in the chat header. Models come from configured LLM providers (see [LLM providers](../configuration/llm-providers.md)).

- Built-in: DeepSeek, Anthropic, OpenAI, Gemini, Ollama
- Custom: OpenAI-compatible endpoints added in **Dashboard > Settings > LLM Providers**

Default provider is marked in admin settings.

## Agent capabilities

During a turn the agent may:

- Call registered tools (filesystem, web, workspace APIs, MCP tools)
- Stream partial responses and thinking blocks
- Propose **mutations** (new tools/skills) for owner approval
- Run slash commands (see below)

Tool iteration limits and context compression are configured under **Dashboard > Settings > Agent behaviour**.

## Slash commands

Type `/` in the input bar to open the slash menu. Examples:

| Command | Purpose |
| --- | --- |
| `/opportunity` | Opportunity engine (see [Opportunity engine](../opportunity-engine.md)) |
| `/research` | Start or continue deep research |
| `/help` | List available commands |

Exact commands depend on installed skills and packs.

## Sessions API

| Action | Endpoint |
| --- | --- |
| List sessions | `GET /api/conversations` |
| Create session | `POST /api/conversations` |
| Send message | `POST /api/conversations/{id}/messages` (streaming) |
| Export session | `GET /api/workspace/sessions/{id}/export` |

Full paths: [API reference](../reference/api.md).

## OpenAI-compatible access

External clients can use `POST /v1/chat/completions` with a developer API key. See [Developer platform](developer-platform.md) and [OpenAI-compatible API](../integrations/openai-api.md).

## Troubleshooting

| Symptom | Check |
| --- | --- |
| No models in selector | Provider keys in `.env` or dashboard LLM settings |
| Tool calls fail | MCP server status, network egress, Scout kill switch |
| Stream stalls | Backend logs, `KEPRIX_MAX_TOOL_ITERATIONS` |
| Cannot start blank chat | Clear cache; ensure latest frontend (no auto-redirect to first session) |

## Related

- [Agent runtime](agent.md)
- [Built-in tools](tools.md)
- [MCP](../integrations/mcp.md)
- [Memory and RAG](memory.md)
