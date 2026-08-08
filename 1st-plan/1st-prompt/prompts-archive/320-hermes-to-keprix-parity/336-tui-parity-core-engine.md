# keprix - Prompt 336: TUI Parity; Core Architecture and Engine

## Purpose

keprix's Python Textual TUI has 57 files and a 20-file Hermes TUI test suite inherited from the fork. Hermes's TypeScript Ink TUI has 358 files with 40+ dedicated unit tests and 20+ integration tests. This is not a cosmetic gap; it's a capability gap.

The TUI is the operator's primary interface. Hermes treats it as a first-class runtime citizen (same process, same event loop). keprix treats it as one of many interfaces alongside the WebUI. This prompt builds the TUI foundation to Hermes-level power while retaining keprix's look, color system, and aesthetic.

## Scope

Rebuild the TUI architecture to match Hermes capability parity across every feature. keprix branding, color theme, visual identity, and text styling remain keprix-native. No Hermes look is copied.

## What Hermes has that keprix doesn't

### Engine-level
- **In-process rendering engine**; Hermes built its own Ink-based renderer (`hermes-ink` package) with custom DOM, flexbox layout, event system, focus management, cursor control, selection, hit testing, mouse support, scroll boxes, ANSI color pipeline, terminal size detection, terminal focus tracking, alternate screen support, and raw mode management
- **Gateway client**; TUI connects to gateway via WebSocket, handles reconnection, authentication, session resume
- **Protocol layer**; Typed protocol for all gateway messages, tool calls, streaming deltas, approvals, slash commands
- **Test framework**; 40+ unit tests for the rendering engine alone (text wrapping, cursor advance, colorize, selection, hit testing, keyboard parsing, terminal I/O, OSC, log-update, resize, mouse), plus 20+ integration tests for TUI features

### Component-level
- **Streaming assistant**; Real-time markdown rendering with syntax highlighting, live token streaming, thinking block scrubber, streaming progress indicator, abort/stop handling
- **Text input**; Multi-line input with history, tab completion, paste handling (OSC 52), masked prompt for sensitive input, cursor navigation, word wrap at terminal width
- **Slash commands**; 30+ native slash commands with fuzzy matching, argument parsing, inline preview, tool search integration, command history
- **App chrome**; Top bar with session title, model indicator, token usage, fps counter, clock, help hint, active session switcher
- **Skills hub**; Browse, search, install, enable/disable skills from the TUI
- **Plugins hub**; Browse, install, configure plugins
- **Agents overlay**; View and manage sub-agents, subagent tree visualization
- **Model picker**; Scrollable model list with provider filters, model metadata, pricing info
- **Todo panel**; Sidebar with live todo list, completion toggling, task management
- **Prompts panel**; Saved prompt library, insert into input
- **Active session switcher**; Switch between open sessions without leaving the TUI
- **Queued messages**; Queue messages while agent is busy, send on completion

### Utility-level
- **Message history**; Infinite scrollback, virtual rendering, message dedup, compression handling
- **External editor**; Launch $EDITOR for multi-line input, seamless reintegration
- **Clipboard**; OSC 52 terminal clipboard, fallback to system clipboard
- **Fuzzy search**; Fuzzy matching for slash commands, skills, model picker, history
- **Terminal setup**; 24-bit truecolor detection, terminal capability probing, graceful degradation
- **Platform detection**; Linux/macOS/Windows/Termux adaptive behavior
- **Emoji support**; Unicode emoji rendering with width detection
- **Math unicode**; Mathematical symbol rendering
- **Live progress**; Progress bars for long operations, spinner animations
- **FPS monitoring**; Built-in FPS counter for performance debugging
- **Virtual viewport**; Render only visible messages, handle 10K+ message histories
- **Syntax highlighting**; Code blocks with language-aware syntax highlighting
- **Memory monitor**; Real-time memory usage display, GC hints

## Tasks

1. **TUI engine hardening**
   - Enhance keprix's `tui/app.py` with proper focus management, raw mode handling, mouse support, terminal size tracking, alternate screen support
   - Enhance `tui/terminal_modes.py` with 24-bit truecolor detection, terminal capability probing
   - Enhance `tui/formatting.py` with proper ANSI color pipeline matching Hermes's colorize.ts
   - Enhance `tui/selection.py` with text selection, copy-to-clipboard, hit testing
   - Add `tui/cursor.py`; cursor advance tracking, cursor declaration, cursor restoration (matches Hermes cursor.ts)
   - Add `tui/viewport.py`; virtual viewport rendering (render only visible messages)
   - Add `tui/mouse.py`; mouse event handling (click, scroll, drag)

2. **Gateway integration**
   - Replace the current polling/HTTP approach with a WebSocket-based gateway client
   - Add `tui/gateway_client.py`; persistent WebSocket, auto-reconnect, authentication, session resume
   - Add `tui/gateway_types.py`; typed protocol messages (stream deltas, tool calls, approvals, slash results)
   - Add `tui/gateway_handler.py`; incoming message dispatch, event routing

3. **Test parity**
   - Add 40+ unit tests covering: text wrapping, cursor advance, colorize, selection, hit testing, keyboard parsing, terminal I/O, resize, mouse events, viewport, ANSI pipeline, OSC clipboard, log-update
   - Add 20+ integration tests: streaming output, slash commands, tool approvals, model switching, session resume, error recovery, interruption handling

## Files to create

```
src/keprix/tui/
  cursor.py                   - cursor tracking and restoration
  viewport.py                 - virtual viewport rendering
  mouse.py                    - mouse event handling
  gateway_client.py           - WebSocket gateway client
  gateway_types.py            - typed protocol messages
  gateway_handler.py          - message dispatch and routing
  focus.py                    - focus management
  raw_mode.py                 - raw terminal mode handling
  hit_test.py                 - hit testing for click/select

tests/tui/
  test_terminal_modes.py      - truecolor detection, capability probing
  test_ansi_pipeline.py       - ANSI colorize, 256-color, truecolor
  test_cursor_advance.py      - cursor tracking
  test_selection.py           - text selection, copy
  test_hit_test.py            - hit testing
  test_viewport.py            - virtual rendering
  test_mouse.py               - mouse events
  test_keyboard_parse.py      - keypress parsing
  test_clipboard_osc52.py     - OSC 52 clipboard
  test_gateway_client.py      - WebSocket connection, reconnect
  test_gateway_protocol.py    - protocol message parsing
```

## Acceptance criteria

- 24-bit truecolor detection works on Linux, macOS, and Windows Terminal
- Mouse click, scroll, and drag events are captured and routed
- Text selection with copy-to-clipboard works via OSC 52
- Gateway WebSocket client reconnects on disconnect with exponential backoff
- Virtual viewport renders 10K+ message histories without performance degradation
- 40+ engine-level unit tests pass
- All existing keprix TUI tests continue to pass
- No Hermes visual identity, branding, or color scheme is copied
