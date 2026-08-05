# Keprix Prompt 202: TUI Tool Approval and Clarify Overlays

## Purpose

When the agent calls **clarify** or requests **dangerous command approval**, the web UI
shows interactive prompts. The TUI currently has no overlay; the turn blocks or fails.
Port Hermes gateway prompt UX as Textual **modal overlays** without changing the chat
color scheme.

Depends on **prompt 201** (live turn registry + interrupt).

---

## Hermes reference

| File | What to port |
| --- | --- |
| `ui-tui/src/components/prompts.tsx` | `ApprovalPrompt`, `ClarifyPrompt`, `approvalAction()` |
| `ui-tui/src/components/maskedPrompt.tsx` | Secret/sudo masked input |
| `ui-tui/src/app/useInputHandlers.ts` | `cancelOverlayFromCtrlC()`, scroll fallthrough |
| `gateway` clarify/approval resolve handlers | Button → RPC respond |

Keprix existing:

- `tools/clarify_tool.py`, `tools/approval` (grep gateway approval)
- `src/keprix/gateway/platforms/` approval button dispatch patterns

---

## Dependencies

- Prompt **201** `TurnRegistry` for session-scoped callbacks
- `src/keprix/tui/app.py`
- Stream events from `POST /api/conversations/{id}/messages` (extend NDJSON if needed)

---

## Stream events (backend)

Ensure NDJSON stream includes prompt events (add if missing):

```json
{"event": "clarify", "clarify_id": "...", "question": "...", "choices": ["A", "B"]}
{"event": "approval", "approval_id": "...", "command": "rm -rf ...", "description": "..."}
{"event": "approval_resolved", "status": "approved"}
```

Wire from existing `clarify_callback` and exec approval hooks used by gateway/web UI.

Add respond endpoints:

```python
POST /api/conversations/{session_id}/clarify/{clarify_id}/respond
  body: { "answer": "A" } | { "text": "freeform" }

POST /api/conversations/{session_id}/approval/{approval_id}/respond
  body: { "decision": "once" | "always" | "deny" }
```

Each endpoint resumes the blocked agent turn (same pattern as gateway
`resolve_gateway_clarify` / `resolve_gateway_approval`).

---

## TUI widgets (new)

```
src/keprix/tui/widgets/
  overlay_base.py      # Modal screen base: Esc, focus trap
  clarify_overlay.py   # Question + numbered choices + freeform fallback
  approval_overlay.py  # Approve once / always / deny
```

Use Textual `ModalScreen` or a full-width `Vertical` with `display: none` toggled; **do not**
change `theme.tcss` colors; reuse existing `#thinking-panel` border style for overlay frame.

### Clarify overlay

- Render question text (markdown via existing `agent_markdown`)
- Keys `1-9` select choice; Enter confirms highlighted
- `a-z` labels if more than 9 choices (match Hermes numbering)
- Esc → cancel with `answer: ""` and system note `Clarify dismissed.`

### Approval overlay

- Show command in monospace block
- `Y` / `Enter` = approve once, `A` = always, `N` / Esc = deny
- Ctrl+C routes to deny (not quit) while overlay open

### Input routing

While overlay visible:

- Composer hidden or read-only
- Global keys handled by overlay first (`shouldFallThroughForScroll` equivalent: PageUp/Down
  still scroll `#message-log`)

---

## Abandoned clarify (Hermes parity)

If user does not respond within `KEPRIX_TUI_CLARIFY_TIMEOUT_SEC` (default 300):

- Auto-dismiss overlay
- Persist abandoned prompt to transcript as system line (port
  `createGatewayEventHandler.flushAbandonedClarify`)

---

## Client (`client.py`)

```python
async def respond_clarify(session_id, clarify_id, answer: str) -> None: ...
async def respond_approval(session_id, approval_id, decision: str) -> None: ...
```

---

## Tests

```
tests/tui/test_clarify_overlay.py      # Pilot tests with Textual pilot
tests/tui/test_approval_overlay.py
tests/api/test_conversation_prompts.py # respond endpoints
```

---

## Acceptance criteria

- [ ] Agent `clarify` tool unblocks when user picks a choice in TUI
- [ ] Exec approval prompts show during terminal tool runs
- [ ] Ctrl+C on overlay cancels prompt, does not exit app
- [ ] Transcript scroll works while overlay is open
- [ ] Stream continues after respond
- [ ] Works with `AUTH_ENABLED=true` (same token as messages)
- [ ] No new colors; overlay uses existing green/dim palette

---

## Out of scope

- Slack/Telegram inline buttons (gateway only)
- Sudo password masked overlay (optional follow-up; stub honestly if deferred)
