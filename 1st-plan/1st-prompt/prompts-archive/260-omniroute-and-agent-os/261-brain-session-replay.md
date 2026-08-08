# Keprix - Prompt 261: Brain session replay

**Status:** Shipped (`brain/session_replay.py`, `api/brain_session_replay_routes.py`, `useBrainReplay.ts`, `BrainReplayTransport.tsx`, `BrainSessionPicker.tsx`, `BrainPathHighlight.tsx`, `BrainReplayExport.tsx`, `BrainGraphPage.tsx` + `BrainGraphCanvas.tsx` replay integration, `tests/brain/test_session_replay.py`, `brain-replay.test.ts`). Note: prompt body header references **253**; canonical queue number is **261** per filename.

---

# Keprix - Prompt 253: Brain Session Replay

## Context

Prompt 250 shows the brain activating in real time during a live conversation.
This prompt adds the ability to replay any past session: step through the conversation
message by message and watch which brain nodes were activated at each step, in the order
they happened.

Session replay turns the brain graph into a debugging and insight tool. A user can
answer questions like: "why did the agent give that answer?" by replaying the session
and seeing exactly which memories fed into each response. It is also useful for onboarding
new team members ("watch how the agent handled this client call").

## What already exists (do not rebuild)

- `retrieval_graph_edges` -- stores activation events with timestamps (Prompt 32 +
  enhanced in Prompt 250 to include session context and timestamps)
- `GET /api/brain/graph?session_id=...` -- returns nodes and edges for one session (Prompt 246)
- `BrainGraphCanvas` from Prompt 247
- Activation animation from Prompt 250 (re-use the pulse animation, driven by replay instead of SSE)

## Prerequisite

Prompt 250 must have added `session_id` and `activated_at` timestamp to
`retrieval_graph_edges`. The replay engine reads these to reconstruct the activation
sequence.

## What to build

### 1. Session replay data API

`src/keprix/brain/session_replay.py`:

```python
class SessionReplayData:
    session_id: str
    session_title: str
    session_date: datetime
    messages: list[ReplayMessage]   # ordered list of conversation turns
    activations: list[ReplayActivation]

@dataclass
class ReplayMessage:
    index: int
    role: str       # "user" | "agent"
    content: str
    timestamp: datetime
    activations_before: list[str]   # node IDs retrieved before this message
    activations_during: list[str]   # node IDs activated while generating the response

@dataclass
class ReplayActivation:
    step: int                       # message index this activation belongs to
    node_kind: str
    node_id: str
    node_label: str
    relation: str                   # "retrieved" | "skill_fired" | "tool_called"
    confidence: float | None
    activated_at: datetime
```

HTTP endpoint:

```
GET /api/brain/sessions/{session_id}/replay
Response: SessionReplayData
```

### 2. Replay engine (client-side)

`frontend/src/hooks/useBrainReplay.ts`:

```typescript
export function useBrainReplay(replayData: SessionReplayData) {
  const [currentStep, setCurrentStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<1 | 2 | 4>(1); // playback speed multiplier
  const [activeNodeIds, setActiveNodeIds] = useState<Set<string>>(new Set());

  // Derived from currentStep: which nodes are active at this point in the replay
  const currentActivations = useMemo(() =>
    replayData.activations.filter(a => a.step === currentStep),
    [replayData, currentStep]
  );

  // Playback: advance one step every (base_interval / speed) ms
  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => {
      setCurrentStep(s => {
        if (s >= replayData.messages.length - 1) {
          setPlaying(false);
          return s;
        }
        return s + 1;
      });
    }, 1500 / speed);
    return () => clearInterval(timer);
  }, [playing, speed, replayData]);

  // Update active node IDs when step changes
  useEffect(() => {
    const ids = new Set(currentActivations.map(a => a.node_id));
    setActiveNodeIds(ids);
    // Auto-clear 2.5 seconds after step ends (if playing)
    // Keep active indefinitely if paused
  }, [currentActivations, playing]);

  return {
    currentStep,
    totalSteps: replayData.messages.length,
    currentMessage: replayData.messages[currentStep],
    activeNodeIds,
    playing,
    speed,
    play: () => setPlaying(true),
    pause: () => setPlaying(false),
    stepForward: () => setCurrentStep(s => Math.min(s + 1, replayData.messages.length - 1)),
    stepBackward: () => setCurrentStep(s => Math.max(s - 1, 0)),
    jumpTo: (step: number) => setCurrentStep(step),
    setSpeed,
  };
}
```

### 3. Replay transport bar

`frontend/src/components/brain/BrainReplayTransport.tsx`:

```
┌──────────────────────────────────────────────────────────────────┐
│  Replaying: "Invoice query chat"  ·  Jan 15, 2026               │
│                                                                  │
│  [◀◀] [◀] [▶/⏸] [▶] [▶▶]   Step 3 / 8    Speed: [1x ▾]       │
│  ━━━━━━━━━━━━━━━━━░░░░░░░░░  [────────────────────────────────] │
│  progress bar                 scrub bar (click to jump to step)  │
│                                                                  │
│  Current turn:                                                   │
│  User: "Can you send the invoice to sarah@example.com?"          │
│  Aiva: "Sure, let me pull up the invoice template now..."        │
│                                                                  │
│  Activated at this step:                                         │
│  [memory] "Client email: sarah@example.com"  retrieved (0.94)   │
│  [skill]  "Send invoice"                     fired              │
│  [tool]   "sendgrid.send_email"              called             │
└──────────────────────────────────────────────────────────────────┘
```

The transport bar sits at the bottom of the page when replay mode is active.
It replaces the live activation timeline (Prompt 250) during replay.

### 4. Session picker

`frontend/src/components/brain/BrainSessionPicker.tsx`:

Accessible from a "Replay session" button in the graph toolbar:

```
[Replay session ▾]
  ├─ Invoice query chat   (Jan 15)  12 activations
  ├─ Tenant enquiry       (Jan 12)  8 activations
  ├─ Payment reminder     (Jan 10)  5 activations
  └─ [View all sessions ->]
```

Selecting a session:
1. Fetches `GET /api/brain/sessions/{id}/replay`
2. Filters the graph to show only nodes touched in this session
3. Opens the replay transport bar
4. Graph dims all non-session nodes (same as focus mode from Prompt 249)
5. Starts paused at step 0

### 5. Graph integration during replay

When the replay step changes:
- Active nodes (for current step) pulse using the same animation as Prompt 250
- The current session node is always highlighted with a ring
- The graph auto-pans to keep the currently-activating nodes in view (if they are
  off screen), unless the user has manually panned (in which case: pause auto-pan)
- Edges connecting the active nodes to the session node animate (Prompt 250 behaviour)

### 6. Path highlighting

When replay is active and paused on a step, the user can click any active node to
see its "contribution path": how that memory connected to the response.

Highlighted path:
```
[session node] -- retrieved_from --> [memory node] -- derived_from --> [document node]
```

Shown as a thick coloured trail over the normal graph edges.

### 7. Replay export

"Export replay" button in the transport bar:

```
Formats:
  [Export transcript]      -- plain text of the conversation with activation notes
  [Export activation log]  -- CSV: step, timestamp, node_kind, node_id, label, relation
```

## Files to create

```
src/keprix/brain/
  session_replay.py              - SessionReplayData, ReplayMessage, ReplayActivation
                                   query: join sessions + messages + retrieval_graph_edges

src/keprix/api/
  brain_session_replay_routes.py - GET /api/brain/sessions/{id}/replay

frontend/src/hooks/
  useBrainReplay.ts              - replay engine: playback, step, speed, active nodes

frontend/src/components/brain/
  BrainReplayTransport.tsx       - transport bar (play/pause/step/scrub)
  BrainSessionPicker.tsx         - session selector dropdown
  BrainPathHighlight.tsx         - contribution path overlay on graph edges
  BrainReplayExport.tsx          - transcript + CSV export
```

## Acceptance criteria

- Session picker lists past sessions ordered by most recent. Shows activation count per session.
- Selecting a session filters the graph to that session's nodes and opens the transport bar.
- Play advances through steps at the correct interval (1.5s at 1x, 0.75s at 2x, 0.375s at 4x).
- At each step, the correct nodes pulse on the canvas and the current message is shown.
- Scrubbing (clicking the progress bar) jumps to any step correctly.
- Step forward/backward buttons move one step at a time.
- Auto-pan keeps active nodes visible unless the user has manually panned.
- Path highlighting shows the connection chain from session to active node correctly.
- Replay export produces a valid transcript and a valid CSV.
- Closing replay (or navigating away) restores the full graph to its pre-replay state.
- Sessions with zero activation events (no edges in `retrieval_graph_edges`) show a clear
  message: "No brain activity recorded for this session."
