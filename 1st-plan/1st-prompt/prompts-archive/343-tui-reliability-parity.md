# Keprix Prompt 343: TUI Reliability Parity

## Goal

Make Keprix TUI as resilient as Hermes TUI under real operator conditions: backend restarts, bad routes, timeouts, missing providers, invalid commands, terminal resize, interrupt during streaming, terminal capability differences, and render failures must not crash or corrupt the terminal.

This prompt is about failure behavior, recovery, and confidence. Do not add new visual features unless needed to communicate failure and recovery clearly.

## Scope

Implement reliability parity for:

- Backend unavailable
- Backend restart
- Session expired
- 404 and 500 API errors
- Network timeout
- Missing provider or setup required
- Invalid slash commands
- Ctrl+C during streaming
- Ctrl+C during tool execution
- Queue and steer while busy
- Terminal resize during streaming
- Terminal exit and raw mode restore
- Termux/basic terminal degradation
- Render error boundary
- Gateway reconnect and resume

## Required behavior

### Backend unavailable

When backend is offline:

- TUI must open without crashing.
- Sidebar/status must show offline state.
- Transcript must show actionable recovery command: `keprix start` or Ctrl+R reconnect.
- Slash commands that do not need backend still work.
- Backend commands show a non-crashing unavailable message.

### Backend restart and session resume

When backend restarts:

- Health check must detect disconnect.
- TUI must retry or allow Ctrl+R reconnect.
- Expired session must be replaced or resumed with a clear message.
- User input must not be lost.
- Streaming panel must clear cleanly if the stream dies.
- Terminal state must remain valid.

### HTTP errors

All API calls used by the TUI must handle:

- 400
- 401
- 403
- 404
- 408
- 429
- 500
- connection error
- timeout

Errors must render as user-readable TUI messages, not tracebacks.

### Missing provider/setup required

When no provider is configured:

- Setup overlay must appear or `/setup` must be available.
- Input must not silently discard text.
- User must receive clear next step.
- TUI must recover after setup is completed.

### Invalid slash commands

Invalid commands must:

- Suggest likely matches where possible
- Fall through to backend only when safe
- Never crash on missing backend route
- Show command unavailable when no handler exists

### Interrupt behavior

Ctrl+C during streaming must:

- Request backend interrupt where available
- Cancel local stream task
- Preserve partial output
- Mark reply interrupted
- Restore input focus
- Preserve queued messages unless explicitly cleared

Ctrl+C during tool execution must not leave the TUI busy forever.

### Busy modes

Reliability for busy modes:

- `interrupt`: Enter interrupts and sends pending text after stop
- `queue`: Enter queues
- `steer`: Enter sends steering note
- Queue count updates immediately
- Queue survives transient stream errors during the active turn

### Resize behavior

Terminal resize must:

- Not crash
- Reflow transcript
- Preserve scroll position where possible
- Refresh sidebar, details, slash picker, and streaming panel
- Work while streaming

### Terminal state restore

On exit, exception, Ctrl+D, Ctrl+C quit, or backend crash:

- Raw mode restored
- Mouse mode disabled
- Bracketed paste disabled
- Alternate screen restored
- Cursor visible
- No terminal control garbage left behind

### Terminal compatibility

Support graceful degradation for:

- Linux desktop terminal
- macOS terminal/iTerm2
- Windows Terminal
- tmux
- screen
- VS Code terminal
- Termux
- Basic terminals with no OSC 52 or truecolor

Unsupported features must disable silently with a visible status only where useful.

### Render error boundary

Render failures must:

- Be caught
- Show concise error overlay/message
- Preserve ability to quit
- Log stack trace for developer inspection
- Avoid recursive crash loops

### Gateway reconnect

Gateway/WebSocket path must:

- Reconnect with backoff
- Resume session when possible
- Re-authenticate when needed
- Surface offline/reconnecting/online state in sidebar/status
- Not duplicate stream events after reconnect

## Implementation guidance

Add fault-injection tests. Do not rely only on mocks that hide integration issues.

Likely files:

```text
src/keprix/tui/client.py
src/keprix/tui/gateway_client.py
src/keprix/tui/gateway_handler.py
src/keprix/tui/graceful_exit.py
src/keprix/tui/terminal_modes.py
src/keprix/tui/terminal_startup.py
src/keprix/tui/error_boundary.py
src/keprix/tui/resize_handler.py
src/keprix/tui/app.py
tests/tui/test_fault_injection.py
tests/tui/test_backend_reconnect.py
tests/tui/test_interrupt_reliability.py
tests/tui/test_terminal_restore.py
tests/tui/test_resize_reliability.py
tests/tui/test_error_boundary.py
```

## Acceptance criteria

- TUI opens when backend is unavailable and does not crash.
- Invalid command and backend 404 render as normal messages.
- Backend restart can be recovered with Ctrl+R or automatic reconnect.
- Session expiration starts or resumes a usable session with clear notice.
- Ctrl+C during streaming preserves partial output and clears busy state.
- Queue, interrupt, and steer modes are tested under busy state.
- Resize during streaming does not crash and refreshes panels.
- Terminal modes are restored on exit and exception.
- Termux/basic terminal profile disables unsupported features.
- Render errors are caught and surfaced.
- All old TUI tests pass.
- New fault-injection tests pass.

## Verification commands

```bash
python -m pytest tests/tui -q
python -m pytest tests/tui/test_fault_injection.py -q
python -m pytest tests/tui/test_interrupt_reliability.py -q
python -m pytest tests/tui/test_terminal_restore.py -q
```

