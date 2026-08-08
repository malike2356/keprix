# Keprix - Prompt 250: Brain Live Session Activation Overlay

## Context

Prompts 246-249 give a static view of the brain. This prompt makes it live: when an agent
conversation is active, the brain graph pulses in real time to show exactly which memories
are being retrieved, which skills are being selected, which documents are being searched.

The user watching the graph during a conversation can see the agent think. A memory lights
up, an edge pulses from it to the current session node, a skill node glows as it fires.
This is the feature that makes keprix's brain graph categorically different from Obsidian,
Notion, or any existing tool.

It also has a practical use: seeing which memories dominate a session helps users spot
over-reliance on stale context and prune accordingly.

## What already exists (do not rebuild)

- `agent/tool_executor.py` -- tool execution (add activation signal emission here)
- `agent/conversation_loop.py` -- conversation state (add retrieval signal emission here)
- `gateway/stream_events.py` -- event routing (add brain activation as a new event type)
- `GET /api/brain/graph` -- static data from Prompt 246
- `BrainGraphCanvas` -- canvas from Prompt 247

## Architecture

```
Agent loop
  |
  | (retrieves memories for context)
  v
ActivationEmitter.emit("memory_retrieved", {id: "mem_abc", session_id: "sess_xyz"})
  |
  v
SSE stream: GET /api/brain/graph/activation-stream?session_id=sess_xyz
  |
  v
BrainGraphCanvas (client, subscribed during active session)
  |
  | onActivation(event) -> pulse node "mem_abc" with glow animation
  v
Canvas shows real-time brain activation
```

SSE (Server-Sent Events) rather than WebSocket because the stream is one-directional:
server emits activation events, client only reads. SSE works through standard HTTP/2,
requires no extra connection management, and is resumable automatically.

## What to build

### 1. Activation emitter

`src/keprix/brain/activation_emitter.py`:

```python
class ActivationEmitter:
    """
    Emits brain activation signals when the agent retrieves or uses a brain item.
    Called from the agent loop, tool executor, and memory retrieval pipeline.
    """

    async def emit(
        self,
        event_type: ActivationEventType,
        *,
        workspace_id: str,
        session_id: str,
        node_kind: str,
        node_id: str,
        relation: str | None = None,     # what the agent is doing with this node
        confidence: float | None = None, # retrieval confidence score if available
    ) -> None:
        """
        Publish an activation event to the workspace SSE channel.
        Non-blocking: if no client is listening, the event is dropped.
        Also persists the edge to retrieval_graph_edges for the static view.
        """

class ActivationEventType(StrEnum):
    MEMORY_RETRIEVED   = "memory_retrieved"
    SKILL_SELECTED     = "skill_selected"
    SKILL_FIRED        = "skill_fired"
    TOOL_CALLED        = "tool_called"
    DOCUMENT_SEARCHED  = "document_searched"
    TASK_READ          = "task_read"
    SESSION_LINKED     = "session_linked"
```

### 2. Emission call sites

Add `ActivationEmitter.emit()` calls at these locations:

`agent/conversation_loop.py` -- after memory retrieval for context injection:
```python
await activation_emitter.emit(
    ActivationEventType.MEMORY_RETRIEVED,
    workspace_id=session.workspace_id,
    session_id=session.id,
    node_kind="memory",
    node_id=memory.id,
    confidence=memory.retrieval_score,
)
```

`agent/tool_executor.py` -- before tool execution:
```python
await activation_emitter.emit(
    ActivationEventType.TOOL_CALLED,
    workspace_id=session.workspace_id,
    session_id=session.id,
    node_kind="tool",
    node_id=tool.name,
    relation="called_in",
)
```

`skills/skill_executor.py` -- when a skill is selected and when it fires:
```python
# on selection:
await activation_emitter.emit(ActivationEventType.SKILL_SELECTED, ...)
# on execution:
await activation_emitter.emit(ActivationEventType.SKILL_FIRED, ...)
```

### 3. SSE endpoint

`src/keprix/api/brain_activation_routes.py`:

```python
GET /api/brain/graph/activation-stream
  Query params: session_id (required)
  Response: text/event-stream

  Event format:
  data: {"type":"memory_retrieved","node_kind":"memory","node_id":"mem_abc123",
         "session_id":"sess_xyz","confidence":0.91,"ts":"2026-01-15T14:23:01Z"}

  Connection lifecycle:
  - Client connects with session_id
  - Server registers the client in an in-memory pub/sub registry keyed by workspace_id
  - Events for that workspace are forwarded to the client
  - On disconnect: client is removed from registry automatically
  - Heartbeat every 15 seconds (empty comment line: ": heartbeat") to keep connection alive
```

In-memory pub/sub (not Redis -- keprix is single-node):
```python
class ActivationBus:
    """Simple asyncio-based pub/sub for SSE delivery."""
    _queues: dict[str, list[asyncio.Queue]] = {}

    def subscribe(self, workspace_id: str) -> asyncio.Queue:
        q = asyncio.Queue(maxsize=100)
        self._queues.setdefault(workspace_id, []).append(q)
        return q

    def unsubscribe(self, workspace_id: str, q: asyncio.Queue):
        self._queues.get(workspace_id, []).remove(q)

    async def publish(self, workspace_id: str, event: dict):
        for q in self._queues.get(workspace_id, []):
            q.put_nowait(event)  # drops if queue full (backpressure)
```

### 4. Client-side SSE hook

`frontend/src/hooks/useBrainActivation.ts`:

```typescript
export function useBrainActivation(sessionId: string | null) {
  const [activeNodeIds, setActiveNodeIds] = useState<Set<string>>(new Set());
  const [recentActivations, setRecentActivations] = useState<ActivationEvent[]>([]);

  useEffect(() => {
    if (!sessionId) return;

    const es = new EventSource(`/api/brain/graph/activation-stream?session_id=${sessionId}`);

    es.onmessage = (e) => {
      const event = JSON.parse(e.data) as ActivationEvent;
      setActiveNodeIds((prev) => new Set([...prev, event.node_id]));
      setRecentActivations((prev) => [event, ...prev].slice(0, 50));

      // Auto-clear the active state after 3 seconds
      setTimeout(() => {
        setActiveNodeIds((prev) => {
          const next = new Set(prev);
          next.delete(event.node_id);
          return next;
        });
      }, 3000);
    };

    return () => es.close();
  }, [sessionId]);

  return { activeNodeIds, recentActivations };
}
```

### 5. Canvas animation

Each custom node component (from Prompt 247) accepts an `active` prop:

```typescript
interface MemoryNodeProps {
  data: GraphNode;
  active?: boolean; // true = currently activated
  dimmed?: boolean; // true = not in current focus
}
```

When `active === true`:
- Node scales from 1.0 to 1.2 over 200ms, then back to 1.0 over 400ms
- A radial glow pulse radiates outward (CSS keyframe: opacity 1 -> 0, scale 1 -> 2)
- Border colour brightens to the kind's accent colour
- Animation repeats twice then stops

When a memory activates, the edge FROM that memory TO the current session node also animates:
- Edge becomes animated (React Flow's `animated: true`)
- Edge colour brightens for 3 seconds then returns to normal

### 6. Activation timeline sidebar

A collapsible timeline panel at the bottom of the graph page:

```
[Brain Activity]  [●] Live (session: "Invoice query chat")
─────────────────────────────────────────────────────────
14:23:01  memory    "Client prefers PDF invoices"       retrieved  conf 0.91
14:23:01  memory    "Client on Net-30 terms"            retrieved  conf 0.87
14:23:02  tool      sendgrid.send_email                 called
14:23:03  skill     "Send payment reminder"             fired
─────────────────────────────────────────────────────────
[Pause]  [Clear]  [Export log]
```

Collapses to a single "● Live" indicator bar when minimised.

### 7. Session selector for live mode

In the filter bar (Prompt 249), a new "Live" toggle:

```
[● Live: current session ▾]
```

Dropdown lists all currently active sessions in this workspace (a user may have
multiple tabs open). Selecting one subscribes to that session's activation stream.
Default: the most recently active session.

## Files to create

```
src/keprix/brain/
  activation_emitter.py          - ActivationEmitter, ActivationEventType
  activation_bus.py              - ActivationBus (asyncio pub/sub)

src/keprix/api/
  brain_activation_routes.py     - GET /api/brain/graph/activation-stream (SSE)

frontend/src/hooks/
  useBrainActivation.ts          - SSE subscription, active node tracking

frontend/src/components/brain/
  BrainActivationTimeline.tsx    - live activity feed at bottom of canvas
  LiveSessionSelector.tsx        - active session picker for live mode
```

Modifications to existing files:
- `agent/conversation_loop.py` -- add `ActivationEmitter.emit()` on memory retrieval
- `agent/tool_executor.py` -- add `ActivationEmitter.emit()` on tool dispatch
- All custom node components (Prompt 247) -- accept and handle `active` prop

## Acceptance criteria

- When a memory is retrieved in an active session, its graph node pulses within 500ms
  in a browser tab that has `/brain/graph` open.
- When a tool is called, the tool node pulses and an animated edge appears from it to
  the current session node.
- The activation timeline shows events in real time with correct timestamps, node kind,
  label, and action label.
- Active node returns to normal appearance within 3 seconds of activation.
- When no session is active, the live stream does nothing; the static graph is unaffected.
- Disconnecting from the SSE stream (tab hidden, network interrupt) reconnects automatically
  when the tab becomes visible (EventSource auto-reconnect).
- The `ActivationBus` drops events silently when the client queue is full; it does not block
  the agent loop.
- Activation events are also persisted as `retrieval_graph_edges` rows so they appear in
  the static graph after the session ends.
- The activation timeline can be exported as a plain text log.
