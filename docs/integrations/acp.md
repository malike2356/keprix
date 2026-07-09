# ACP - Agent Communication Protocol

Agent Communication Protocol (ACP) is an open standard for agent-to-agent and agent-to-runtime interoperability. Keprix implements ACP so your instance can communicate with other ACP-compatible agent runtimes, send and receive structured task messages, and participate in federated multi-agent workflows.

## What ACP provides

| Capability | Description |
| --- | --- |
| Structured messaging | Typed task and result envelopes across agent runtimes |
| Discovery | Agents advertise capabilities via ACP manifests |
| Delegation | One runtime delegates sub-tasks to another |
| Streaming | Incremental progress events over SSE |
| Auth | JWT-based identity verification across instances |

ACP is distinct from [MCP](mcp.md) (Model Context Protocol): MCP connects an agent to **tools**, ACP connects an agent **runtime** to other **runtimes**.

## Configuration

Enable and configure ACP in `.env`:

```bash
KEPRIX_ACP_ENABLED=true
KEPRIX_ACP_ENDPOINT=https://your-domain.com/acp    # public URL this instance listens on
KEPRIX_ACP_TRUSTED_PEERS=https://peer-a.example.com,https://peer-b.example.com
KEPRIX_ACP_JWT_SECRET=your-shared-secret           # or use asymmetric keys
KEPRIX_ACP_ALLOW_INBOUND_DELEGATION=true           # accept delegated tasks from peers
```

## CLI

Start the ACP gateway manually (usually managed by Docker Compose):

```bash
python3 -m keprix.keprix_cli.main acp
```

Check ACP status:

```bash
python3 -m keprix.keprix_cli.main acp status
```

List known peers:

```bash
python3 -m keprix.keprix_cli.main acp peers
```

## ACP API endpoints

When `KEPRIX_ACP_ENABLED=true`, the following routes are mounted:

| Endpoint | Purpose |
| --- | --- |
| `GET /acp/manifest` | Advertise this instance's capabilities |
| `POST /acp/tasks` | Accept an inbound delegated task |
| `GET /acp/tasks/{id}` | Poll task status |
| `GET /acp/tasks/{id}/events` | Stream task progress (SSE) |
| `POST /acp/tasks/{id}/cancel` | Cancel a running delegated task |

## Sending a task to a peer

Using the SDK:

```python
from keprix import KeprixClient

client = KeprixClient(base_url="http://localhost:3333", api_key="...")

result = client.acp.delegate(
    peer_url="https://peer-a.example.com",
    task={
        "objective": "Scan this domain for open ports",
        "inputs": {"domain": "example.com"},
        "capabilities_required": ["network.scan"],
    },
)

for event in result.stream():
    print(event)
```

## Manifest format

Keprix advertises a capability manifest at `/acp/manifest`:

```json
{
  "agent_id": "keprix-instance-uuid",
  "name": "Keprix CE",
  "version": "1.0.0",
  "capabilities": [
    "research.deep",
    "code.execute",
    "workspace.tasks",
    "tools.mutation"
  ],
  "acp_version": "1.0",
  "endpoint": "https://your-domain.com/acp"
}
```

Skills and packs declare their ACP capabilities in their manifests. Installing a pack that declares `network.scan` adds that capability to your ACP advertisement.

## Federated workflows

ACP enables workflows where a primary Keprix instance orchestrates multiple specialised instances:

```
Orchestrator Keprix
  -> [ACP delegate] Research agent (Keprix B)
  -> [ACP delegate] Security scanner (external instance)
  -> [ACP delegate] Report writer (Keprix C)
  -> Aggregate results and produce final output
```

This is set up via Agent Teams (use `acp_peer` as the agent type) or directly via the ACP API.

## Security

- All inbound ACP requests are verified against `KEPRIX_ACP_TRUSTED_PEERS`.
- JWT tokens are short-lived (15 minutes, configurable with `KEPRIX_ACP_TOKEN_TTL`).
- Delegated tasks run under a restricted system user; they cannot access vault secrets unless explicitly granted.
- Inbound delegation can be disabled entirely with `KEPRIX_ACP_ALLOW_INBOUND_DELEGATION=false`.

## Related

- [MCP integration](mcp.md)
- [Agent teams](../features/agent-teams.md)
- [Agent Studio](../features/agent-studio.md)
- [Security architecture](../security/architecture.md)
