# keprix - Prompt: Terminal UI (TUI)

## Purpose

When keprix was forked, the original TUI was stripped. Users currently have only the CLI (`keprix chat` which starts a basic readline loop). This prompt builds a proper terminal UI so users get a rich interactive experience without leaving the terminal.

The TUI must feel like a native terminal application: fast, keyboard-driven, and information-dense. It adopts the interaction patterns from Carina's WebUI (model selector, session list, streaming messages, thinking indicator) but renders them in the terminal using a TUI framework.

## Framework choice

Use **Textual** (Python). It is the most mature Python TUI framework, has built-in widgets for the patterns we need (lists, inputs, markdown rendering, layouts), and keeps the TUI code in the same language as the keprix backend.

The TUI runs as a keprix CLI subcommand:

```bash
keprix tui                  # Start TUI
keprix tui --session ID     # Resume a session
keprix tui --model MODEL    # Start with specific model
```

## Architecture

```
keprix/
  tui/
    __init__.py
    app.py                  - Textual App subclass, entry point
    screens/
      chat.py               - main chat screen
      sessions.py           - session list / picker
      settings.py           - quick settings (model, provider)
    widgets/
      message_list.py       - scrollable message feed
      message_row.py        - single message (user or agent)
      input_bar.py          - multi-line input with send
      thinking_panel.py     - collapsible agent thinking
      model_selector.py     - model/provider picker
      session_sidebar.py    - session list sidebar
      status_bar.py         - bottom status line
    api/
      client.py             - HTTP client to keprix backend
      streaming.py          - SSE stream consumer
    styles/
      theme.tcss            - Textual CSS theme

keprix_cli/
  tui_commands.py           - CLI entry points for 'keprix tui'
```

## Screens

### Chat screen (primary)

The main screen the user spends time in. Layout:

```
+--SessionList---+----------------------------------------+
| New Chat       |  Session: "Debug the deployment"       |
|                |                                        |
| Debug the dep. |  [User] Check the nginx config         |
| Fix providers  |                                        |
| Research proj. |  [Agent] I will check the nginx config |
|                |  on your instance.                     |
|                |                                        |
|                |  [Thinking] running: terminal           |
|                |    command: cat /etc/nginx/nginx.conf   |
|                |    ...                                  |
|                |                                        |
|                |  [Agent] Here is the nginx config:     |
|                |  ```                                   |
|                |  server { listen 80; ...               |
|                |  ```                                   |
|                |                                        |
+----------------+----------------------------------------+
| Model: claude-sonnet-4  | Sessions: 12 | keprix v2.1.0 |
+----------------+----------------------------------------+
| > _                                                    |
+--------------------------------------------------------+
```

### Session list

When the user presses Ctrl+S or clicks the sidebar, a session picker overlay appears:

- List of recent sessions with title, message count, last active time.
- Filter as you type.
- Enter to open, Delete to remove, Escape to cancel.
- "New Chat" always at the top.

### Settings overlay

Quick settings overlay (Ctrl+,):

- Model selector: list of available models, Enter to select.
- Provider key status: shows which providers have keys configured.
- Theme toggle: light/dark.
- Escape to close.

## Widgets

### Message List

- Virtual scrolling for performance with hundreds of messages.
- User messages right-aligned, agent messages left-aligned.
- Agent messages rendered as Markdown (headings, lists, code blocks, bold, italic, links).
- Code blocks with syntax highlighting (using `rich` for highlighting, already a Textual dependency).
- Timestamps shown on hover or with a toggle key (Ctrl+T).
- System messages (tool calls, errors) in a muted style.
- Scroll to bottom on new messages. "Jump to bottom" button if scrolled up.

### Thinking Panel

When the agent is processing, show a collapsible thinking panel:

```
[Thinking] 3 steps
  completed  running: web_search("nginx config best practices")
  error      failed: terminal("cat /etc/nginx/nginx.conf") -- permission denied
  pending    next: terminal("sudo cat /etc/nginx/nginx.conf")
```

- Steps appear in real time as the agent reports them.
- Completed steps show a summary of the result.
- Failed steps show the error in red.
- Panel auto-collapses when the agent finishes.
- Toggle with Ctrl+W.

### Input Bar

- Multi-line input (Shift+Enter for new line, Enter to send).
- Character count (no hard limit, but visual indicator at 4000 chars).
- Input history (up/down arrows to navigate previous messages).
- Ctrl+C while empty exits the TUI (with confirmation).
- Paste support for multi-line content.
- "/" commands for quick actions:
  - `/model` -- open model selector.
  - `/sessions` -- open session list.
  - `/clear` -- clear current input.
  - `/quit` -- exit TUI.
  - `/help` -- show keybindings.

### Status Bar

Bottom bar showing:

- Current model (e.g., "claude-sonnet-4").
- Session count.
- keprix version.
- Connection status (green dot = connected, red dot = disconnected, yellow = reconnecting).

## Keybindings

| Key | Action |
| --- | --- |
| Enter | Send message |
| Shift+Enter | New line in input |
| Ctrl+S | Open session list |
| Ctrl+, | Open settings |
| Ctrl+W | Toggle thinking panel |
| Ctrl+T | Toggle timestamps |
| Ctrl+N | New chat |
| Ctrl+L | Clear screen (redraw) |
| Ctrl+C (empty input) | Exit TUI |
| Ctrl+C (during streaming) | Stop generation |
| Up/Down (input) | Navigate input history |
| PageUp/PageDown | Scroll message list |
| Home/End | Jump to top/bottom |
| Escape | Close overlay / cancel |

## API Client

The TUI communicates with the keprix backend via HTTP, same as the WebUI:

```python
class KeprixClient:
    def __init__(self, base_url: str = "http://localhost:3333"):
        self.base_url = base_url
        self.token: str | None = None

    async def list_sessions(self) -> list[Session]:
        """GET /api/sessions"""

    async def get_session(self, session_id: str) -> Session:
        """GET /api/sessions/{id}"""

    async def create_session(self, title: str | None = None) -> Session:
        """POST /api/sessions"""

    async def delete_session(self, session_id: str) -> None:
        """DELETE /api/sessions/{id}"""

    async def send_message(self, session_id: str, message: str) -> AsyncIterator[StreamEvent]:
        """POST /api/sessions/{id}/chat -- SSE stream"""

    async def list_models(self) -> list[Model]:
        """GET /api/models"""

    async def set_model(self, session_id: str, model: str) -> None:
        """POST /api/sessions/{id}/model"""

    async def health_check(self) -> bool:
        """GET /api/health"""
```

The client authenticates using the keprix identity token from `~/.keprix/identity/`. If no identity exists, the TUI prompts the user to run `keprix setup` first.

## Streaming

The TUI consumes the SSE (Server-Sent Events) stream from the backend:

```
event: message
data: {"type": "text", "content": "I will check"}

event: message
data: {"type": "text", "content": " the nginx config."}

event: tool_call
data: {"type": "tool_call", "tool": "terminal", "args": {"command": "cat /etc/nginx/nginx.conf"}}

event: tool_result
data: {"type": "tool_result", "tool": "terminal", "result": "server { listen 80;..."}

event: thinking
data: {"type": "thinking", "content": "The nginx config shows port 80. I should suggest..."}

event: done
data: {"type": "done"}
```

The TUI handles each event type:

- `text`: append to the current agent message, re-render Markdown.
- `tool_call`: add a step to the thinking panel as "running".
- `tool_result`: update the step to "completed" or "error".
- `thinking`: add reasoning text to the thinking panel.
- `done`: finalise the agent message, collapse thinking panel.

## Error handling

- Connection lost: show a "Reconnecting..." banner with a countdown. Auto-retry every 3 seconds.
- API error: show error message in the chat (not a crash). Offer retry.
- Stream interrupted: show partial message with "[response interrupted]" marker.
- Timeout: if no events for 60 seconds, show a warning and offer to stop waiting.

## Startup flow

1. User runs `keprix tui`.
2. TUI checks backend health at `GET /api/health`.
3. If unhealthy: "keprix backend is not running. Start it with: keprix start". Exit with instructions.
4. If healthy: load sessions from `GET /api/sessions`.
5. If sessions exist: open the most recent session.
6. If no sessions: show welcome screen with suggested first prompts.
7. Load available models from `GET /api/models`.

## Welcome screen (first run)

```
keprix TUI v2.1.0

No sessions yet. Start a conversation:

  [1] "Summarise the keprix documentation"
  [2] "Help me configure an LLM provider"
  [3] "Show me what tools are available"
  [4] Type your own message

Or press Ctrl+S to see your sessions, Ctrl+, for settings.

Type a message or select a prompt:
```

## Theme

The TUI uses Textual's built-in theme system with a dark keprix theme:

```css
/* keprix/tui/styles/theme.tcss */
Screen {
  background: #0d1117;
  color: #c9d1d9;
}

#session-list {
  background: #161b22;
  border-right: solid #30363d;
  width: 28;
}

#message-list {
  background: #0d1117;
}

.user-message {
  background: #1f6feb;
  color: #ffffff;
  border: none;
  padding: 1 2;
  margin: 1 0;
  width: auto;
  max-width: 80%;
  align: right middle;
}

.agent-message {
  background: #161b22;
  color: #c9d1d9;
  border: solid #30363d;
  padding: 1 2;
  margin: 1 0;
}

.thinking-panel {
  background: #0d1117;
  border: dashed #30363d;
  padding: 1 2;
  margin: 1 0;
}

#input-bar {
  background: #161b22;
  border-top: solid #30363d;
  padding: 1 2;
  height: auto;
  min-height: 3;
  max-height: 10;
}

#status-bar {
  background: #161b22;
  color: #8b949e;
  height: 1;
}

StatusBar.status-connected {
  color: #3fb950;
}

StatusBar.status-disconnected {
  color: #f85149;
}
```

Colours match the keprix brand (same dark palette as the WebUI).

## Dependencies

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
tui = [
    "textual>=1.0.0",
    "rich>=13.0.0",       # already a Textual dependency
    "httpx>=0.27.0",      # async HTTP client for SSE
]
```

## Tests

```
tests/tui/
  test_client.py          - API client: session CRUD, model list, health check
  test_streaming.py       - SSE parsing: all event types, malformed events, timeout
  test_widgets.py         - widget rendering: messages, thinking, input
  test_keybindings.py     - all documented keybindings function correctly
  test_startup.py         - health check flow, welcome screen, session resume
  test_theme.py           - dark theme applied, colours match spec
```

## Acceptance criteria

- `keprix tui` starts and connects to a running keprix backend.
- User can send a message and see the agent response stream in real time.
- Thinking steps appear during agent processing and collapse on completion.
- Session list shows recent chats; selecting one loads its messages.
- Model selector allows switching models mid-session.
- Code blocks in messages render with syntax highlighting.
- Connection loss shows a reconnection banner; recovery resumes the session.
- All keybindings documented above work.
- `keprix tui --session ID` resumes a specific session.
- Theme is dark by default matching the keprix colour palette.
- No Carina brand strings, emojis, em dashes, or placeholder text in UI copy.
