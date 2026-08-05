# keprix - Prompt 339: TUI Parity; Message Display, History, and Terminal Integration

## Purpose

Hermes's TUI reads like a native terminal application, not a web app ported to the terminal. Every detail of message display, history navigation, and terminal integration is polished. keprix's TUI renders messages as basic text blocks with formatting shortcuts.

This prompt builds the message rendering system, virtual history, clipboard integration, external editor support, and terminal-specific features that make the TUI feel professional. keprix aesthetic applies.

## What Hermes has that keprix doesn't

### Message rendering
- **Message grouping**; Consecutive messages from the same role are visually grouped with subtle separators
- **Role indicators**; User messages prefixed with `>` or user icon, assistant messages with agent name/avatar
- **Timestamp display**; Per-message timestamps, relative time ("2m ago"), absolute on hover
- **Tool call rendering**; Inline tool name + args summary, expandable to full args, status badge (running/done/error)
- **Tool result truncation**; Long tool results show first 500 chars with "Show more..." expander
- **Error display**; Error messages shown in red with error type and suggestion
- **File reference rendering**; Inline file paths as clickable links (open in $EDITOR)
- **URL rendering**; Inline URLs as clickable links (open in browser)
- **Image reference**; MEDIA: path rendered as thumbnail description
- **Citation rendering**; Footnote-style citations, hover to see source URL

### Virtual history
- **Infinite scrollback**; Messages loaded on demand from session DB, not held entirely in memory
- **Virtual rendering**; Only visible messages are rendered (10K+ message sessions work)
- **Scroll position preservation**; Scroll position maintained across resize events, new messages don't jump
- **Search in history**; Ctrl+F searches message content, jumps to match, highlights all matches
- **Jump to bottom**; Auto-scroll toggle (follow new messages / stay at current position)
- **Message dedup**; Consecutive identical messages collapsed with "[X duplicates]" indicator

### Clipboard integration
- **OSC 52**; True terminal clipboard access via OSC 52 escape sequences
- **Copy message**; Ctrl+Shift+C copies current message to clipboard
- **Copy selection**; Mouse selection copies to clipboard on release
- **Multi-line copy**; Multi-line selection copies with proper formatting
- **Copy code block**; Dedicated shortcut to copy a code block's content

### External editor
- **$EDITOR integration**; Ctrl+X opens current input in $EDITOR, saves on exit, returns to TUI
- **$VISUAL fallback**; Falls back to $VISUAL if $EDITOR is unset
- **Temp file management**; Creates temp file, watches for changes, cleans up on close
- **File reference auto-insert**; Saving a file path inserts it as a reference

### Terminal features
- **Terminal title**; Sets terminal window title to "keprix; [session title]"
- **Notifications**; Bell/beep on message completion when terminal is in background
- **Window resize handling**; Graceful reflow on terminal resize
- **Alternate screen**; Full-screen mode with clean exit (restores terminal on quit)
- **Raw mode**; Proper raw terminal mode with signal handling
- **Graceful exit**; Ctrl+D or `/quit` exits cleanly, restores terminal state
- **Termux support**; Android Termux compatibility (no alternate screen, limited colors)

## Tasks

1. **Message rendering engine**
   - Build `tui/message_renderer.py`; role indicators, timestamps, message grouping, expandable tool calls
   - Build `tui/message_types.py`; typed message envelope (user, assistant, tool_call, tool_result, error, system)
   - Add tool call expand/collapse with status badges
   - Add file path and URL detection with clickable links
   - Add citation rendering with source URL on hover

2. **Virtual history**
   - Build `tui/virtual_history.py`; on-demand message loading from session DB
   - Build `tui/virtual_renderer.py`; render only visible messages, handle 10K+ sessions
   - Add scroll position preservation across resize events
   - Add search-in-history with highlight and jump
   - Add auto-scroll toggle (follow / stay)

3. **Clipboard**
   - Enhance `tui/clipboard.py` with OSC 52 support (true terminal clipboard)
   - Add copy message shortcut (Ctrl+Shift+C)
   - Add copy code block shortcut
   - Add mouse selection auto-copy

4. **External editor**
   - Enhance `tui/external_editor.py` with $EDITOR/$VISUAL detection
   - Add temp file management with change watching
   - Add file reference auto-insert on save

5. **Terminal features**
   - Build `tui/terminal_title.py`; set window title to session name
   - Build `tui/notifications.py`; bell on message completion
   - Build `tui/resize_handler.py`; graceful reflow on terminal resize
   - Build `tui/alternate_screen.py`; full-screen mode with clean restore
   - Build `tui/graceful_exit.py`; clean shutdown, restore terminal state, save session
   - Add Termux compatibility mode

## Files to create

```
src/keprix/tui/
  message_renderer.py          - message display engine
  message_types.py             - typed message envelopes
  virtual_history.py           - on-demand history loading
  virtual_renderer.py          - virtual rendering for 10K+ messages
  history_search.py            - search-in-history with highlight
  terminal_title.py            - window title management
  notifications.py             - bell/beep notifications
  resize_handler.py            - terminal resize handling
  alternate_screen.py          - full-screen mode
  graceful_exit.py             - clean shutdown and restore

tests/tui/
  test_message_renderer.py
  test_virtual_history.py
  test_virtual_renderer.py
  test_clipboard_osc52.py
  test_external_editor.py
  test_terminal_title.py
  test_resize_handler.py
```

## Acceptance criteria

- Messages render with role indicators, timestamps, and proper grouping
- Tool calls show expandable details with status badges (running/done/error)
- File paths and URLs in messages are clickable (open in editor/browser)
- 10K+ message sessions render without performance degradation
- Search-in-history finds and highlights matches with jump navigation
- OSC 52 clipboard works on supported terminals (Kitty, WezTerm, foot, iTerm2)
- Ctrl+X opens input in $EDITOR, returns to TUI on save
- Terminal title shows "keprix; [session title]"
- Terminal state is fully restored on exit (no leftover raw mode)
- keprix colors used throughout message rendering
