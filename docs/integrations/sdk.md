# SDK

Keprix ships TypeScript and Python SDKs for building custom apps, scripts, and integrations on top of your self-hosted instance.

## Overview

The SDK wraps the Keprix REST API with typed clients, streaming helpers, and convenience abstractions for common patterns: sending messages, reading memory, running playbooks, and subscribing to event streams.

## Python SDK

### Installation

```bash
pip install keprix-sdk
# or from source
pip install -e sdk/python/
```

### Quickstart

```python
from keprix import KeprixClient

client = KeprixClient(
    base_url="http://localhost:3333",
    api_key="your-developer-api-key",
)

# Send a message and stream the reply
with client.conversations.create() as session:
    for chunk in session.send("Summarise my open tasks", stream=True):
        print(chunk.content, end="", flush=True)
```

### Authentication

Create a developer API key in **Workspace > Developer > API Keys** (`/developer`). Pass it as:

- Header: `Authorization: Bearer <key>`
- Constructor: `KeprixClient(api_key="...")`
- Environment: `KEPRIX_API_KEY=...`

### Core modules

| Module | Import | Purpose |
| --- | --- | --- |
| Conversations | `client.conversations` | Create sessions, send messages, stream replies |
| Memory | `client.memory` | Store, search, and delete memory documents |
| Tools | `client.tools` | List tools, call tools directly |
| Playbooks | `client.playbooks` | Start and monitor playbook runs |
| Files | `client.files` | Upload and retrieve workspace files |
| Events | `client.events` | Subscribe to server-sent event streams |

### Sending messages

```python
# Non-streaming
response = client.conversations.send(
    session_id="session-uuid",
    message="What is in my inbox?",
)
print(response.content)

# Streaming
for event in client.conversations.stream(
    session_id="session-uuid",
    message="Draft a reply to the last email",
):
    if event.type == "content":
        print(event.delta, end="")
    elif event.type == "tool_call":
        print(f"\n[tool: {event.tool_name}]")
    elif event.type == "done":
        break
```

### Working with memory

```python
# Store a memory
client.memory.add(
    content="The client prefers bullet-point summaries.",
    source="user-preference",
    tags=["style"],
)

# Search memory
results = client.memory.search("client preferences", top_k=5)
for r in results:
    print(r.score, r.content[:100])

# Delete all memories from a source
client.memory.delete_by_source("user-preference")
```

### Running a playbook

```python
run = client.playbooks.start(
    playbook_id="daily-digest",
    inputs={"date": "2026-07-06"},
)

# Poll until done
for event in client.playbooks.stream_events(run.id):
    print(event.type, event.data)
```

### OpenAI-compatible mode

The Keprix API is compatible with the OpenAI Python SDK:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:3333/v1",
    api_key="your-developer-api-key",
)

response = client.chat.completions.create(
    model="anthropic/claude-sonnet-4-6",
    messages=[{"role": "user", "content": "Hello"}],
    stream=True,
)
for chunk in response:
    print(chunk.choices[0].delta.content or "", end="")
```

See [OpenAI-compatible API](openai-api.md) for supported endpoints.

## TypeScript SDK

### Installation

```bash
npm install @keprix/sdk
# or
pnpm add @keprix/sdk
```

### Quickstart

```typescript
import { KeprixClient } from "@keprix/sdk";

const client = new KeprixClient({
  baseUrl: "http://localhost:3333",
  apiKey: process.env.KEPRIX_API_KEY!,
});

const session = await client.conversations.create();
const stream = client.conversations.stream(session.id, "List my tasks");

for await (const chunk of stream) {
  if (chunk.type === "content") process.stdout.write(chunk.delta);
}
```

### TypeScript types

All API responses are fully typed. Import individual types:

```typescript
import type {
  Conversation,
  Message,
  MemoryDocument,
  PlaybookRun,
  ToolManifest,
} from "@keprix/sdk/types";
```

### Agent app integration

The TypeScript SDK is the standard way to build **agent apps** on Keprix. An agent app is a manifest-driven application that runs inside the Agent Apps runner (`/agent-apps`).

```typescript
// agent-app.ts
import { defineAgentApp } from "@keprix/sdk/agent-app";

export default defineAgentApp({
  name: "daily-standup",
  description: "Reads tasks and emails, generates standup notes",
  async run(ctx) {
    const tasks = await ctx.client.workspace.tasks.list({ status: "in_progress" });
    const emails = await ctx.client.email.recent(5);
    const note = await ctx.agent.ask(
      `Summarise these for a 2-minute standup:\nTasks: ${JSON.stringify(tasks)}\nEmails: ${JSON.stringify(emails)}`
    );
    await ctx.client.workspace.notes.create({ title: "Standup", body: note });
  },
});
```

`defineAgentApp` is the planned TypeScript helper for first-party SDK apps. Today, production apps use manifest folders plus the REST runner:

```http
POST /api/agent-apps/{name}/run
Authorization: Bearer <api_key>
Content-Type: application/json

{"inputs": {"focus": "Billing"}, "runner": "api"}
```

See [Agent Apps](../features/agent-apps.md) for manifests, CLI scaffold, and billing limits.

## Developer portal

The in-app developer portal at `/developer` provides:

- API key management (create, revoke, usage stats)
- SDK code examples pre-filled with your instance URL
- Interactive API explorer (links to `/api/docs`)
- Webhook configuration

## API manifest

```http
GET /api/developer/platform
```

Returns instance metadata: OpenAPI URL, SDK download links, supported features.

## Related

- [Developer platform](../features/developer-platform.md)
- [OpenAI-compatible API](openai-api.md)
- [REST API reference](../reference/api.md)
- [Agent Apps](../features/agent-apps.md)
