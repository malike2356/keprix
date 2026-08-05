# Keprix Prompt 201: TUI Steer Mode and Busy Input

## Purpose

Port Hermes **busy input modes** (`interrupt`, `queue`, `steer`) to the Keprix Textual TUI
without changing the green terminal visual theme. Users must be able to **inject guidance
mid-turn** (steer) instead of only queueing or interrupting.

Read `prompts-archive/ref-tui-hermes-parity-architecture.md`. Builds on shipped TUI MVP
(`src/keprix/tui/`). Agent-side steer already exists (`agent._pending_steer`,
`tool_executor._apply_pending_steer_to_tool_results`); this prompt wires HTTP + TUI UX.

---

## Hermes reference (behavior only)

| File | What to port |
| --- | --- |
| `ui-tui/src/app/useSubmission.ts` | `handleBusyInput()`, queue vs steer vs interrupt |
| `ui-tui/src/app/useConfigSync.ts` | `normalizeBusyInputMode()` |
| `ui-tui/src/app/slash/commands/core.ts` | `/busy`, `/steer` RPC |
| `ui-tui/src/app/uiStore.ts` | `busyInputMode` state |

---

## Dependencies

- `src/keprix/tui/app.py` (queue, interrupt, Ctrl+C)
- `src/keprix/agent/agent_init.py` (`_pending_steer`)
- `src/keprix/cli-config.yaml.example` (`display.busy_input_mode`)
- `src/keprix/keprix_cli/web_server.py` (config display keys)
- Active conversation runner for a session (identify where web chat holds in-flight `AIAgent`)

---

## Backend: control-plane API

Add routes (new module `src/keprix/api/tui_control_routes.py` or extend `conversation_routes.py`):

```python
GET  /api/conversations/{session_id}/turn-status
POST /api/conversations/{session_id}/steer
POST /api/conversations/{session_id}/interrupt
```

### `GET .../turn-status`

Response:

```json
{
  "busy": true,
  "mode": "steer",
  "queue_depth": 2,
  "partial_chars": 412
}
```

### `POST .../steer`

Body: `{ "text": "Focus on nginx only" }`

Behavior:

1. Auth same as message send.
2. If no active agent turn for `session_id`, return `409` with `{ "error": "not_busy" }`.
3. Set `agent._pending_steer` (thread-safe via `_pending_steer_lock`) on the live agent
   instance attached to that session's stream.
4. Return `{ "ok": true, "queued_chars": N }`.

Implementation note: the web chat stream handler must register the active `AIAgent` (or a
session-scoped steer queue) in a `TurnRegistry` dict keyed by `session_id`, cleared on
`message_done` / disconnect. Document the registry in module docstring.

### `POST .../interrupt`

Body: optional `{ "keep_queue": true }`

Behavior:

1. Set `agent._interrupt_requested = True` on live turn (same registry).
2. Cancel SSE/NDJSON generator if possible.
3. Return `{ "ok": true }`.

### Config exposure

`GET /api/tui/config` (or reuse existing config endpoint):

```json
{
  "busy_input_mode": "queue",
  "busy_input_modes": ["interrupt", "queue", "steer"]
}
```

Read from `display.busy_input_mode` in loaded config.

---

## TUI client (`src/keprix/tui/client.py`)

```python
async def get_turn_status(self, session_id: str) -> TurnStatus: ...
async def steer(self, session_id: str, text: str) -> None: ...
async def interrupt(self, session_id: str, *, keep_queue: bool = False) -> None: ...
async def get_tui_config(self) -> TuiConfig: ...
```

---

## TUI app behavior (`app.py`)

### Mode-aware submit (replace naive queue-only path)

On Enter while `streaming`:

| Mode | Action |
| --- | --- |
| `queue` | Enqueue (current behavior) |
| `steer` | `POST steer` with composer text; show system line `Steered: ...`; do NOT enqueue |
| `interrupt` | `POST interrupt`; optionally enqueue message for retry after stop |

Load mode on mount and on `/busy` change from config API.

### Slash commands

Extend `slash_commands.py`:

- `/busy` or `/busy queue|steer|interrupt` (local override for session; persist optional in
  `~/.keprix/tui.json` if no write to global config)
- `/steer <text>` always calls steer API (even when mode is queue)

### Status bar

Show `Mode: steer` when not default.

### User feedback

- Steer success: dim system message `Note injected into current turn.`
- Steer when not busy: `Agent is not running. Message sent as new turn.` (fall back to normal send)

---

## Tests

```
tests/tui/test_busy_input.py
tests/api/test_conversation_steer.py
```

Cases:

- `busy_input_mode=steer`: submit while streaming calls steer endpoint, not queue
- Steer text appears in agent tool result on next tool call (integration with mocked agent)
- Interrupt clears busy; partial reply preserved with `*[interrupted]*`
- `GET turn-status` reflects busy state
- Registry does not leak agents after stream completes

---

## Acceptance criteria

- [ ] `display.busy_input_mode: steer` honored by TUI when user presses Enter during a turn
- [ ] `/steer` and `/busy steer` documented in `/help`
- [ ] Steer uses same marker format as CLI (`format_steer_marker`)
- [ ] No duplicate agent processes per session
- [ ] Existing queue + interrupt behavior unchanged when mode is `queue` or `interrupt`
- [ ] No visual theme changes (only behavior + status copy)
- [ ] No emojis, em dashes, or placeholder stubs

---

## Out of scope

- Image/file steer attachments (Hermes limits steer to text; match that)
- Gateway WebSocket RPC (HTTP only for TUI)
