# keprix - Prompt 338: TUI Parity; App Chrome, Panels, and Hubs

## Purpose

Hermes's TUI presents a complete application shell: top bar with session metadata, collapsible side panels for todos and prompts, skills and plugins hubs for browsing and management, agent overlays for sub-agent monitoring, and model picker for switching. keprix's TUI is bare; the chat input and output, plus a few basic overlays.

This prompt builds the full application chrome, panels, and hubs that make the TUI feel like an integrated workspace rather than a chat window.

keprix branding and aesthetic apply throughout. No Hermes look copied.

## What Hermes has that keprix doesn't

### App chrome
- **Top bar**; Session title (auto-generated or user-set), model name and provider badge, token usage counter (session + lifetime), FPS counter overlay toggle, clock/uptime
- **Bottom status bar**; Input mode indicator (insert/overwrite), file modified indicator, gateway connection status, agent busy/idle indicator
- **App layout**; Resizable panels: main chat area, collapsible left sidebar (todos, prompts, sessions), collapsible right sidebar (details, agent tree)

### Sidebars and panels
- **Todo panel**; Live todo list from agent's todo tool, completion toggling, add/remove/edit items, auto-sync with agent state, collapse when empty
- **Prompts panel**; Saved prompt library, search/filter, click to insert into input, categories/folders, recently used
- **Session switcher**; List of open sessions with title/preview/last-active, Ctrl+Tab to cycle, click to switch, close session, fork session
- **Details panel**; Current message metadata (tokens, latency, model, temperature), tool call trace, API request/response inspector

### Overlays
- **Agents overlay**; Tree view of sub-agents, click to expand, live status (running/idle/done/error), output preview, terminate/retry
- **Skills hub overlay**; Browse/search available skills, descriptions, install/uninstall, enable/disable, view SKILL.md source
- **Plugins hub overlay**; Browse installed plugins, configure, enable/disable, marketplace search
- **Model picker overlay**; Scrollable list grouped by provider, model name + pricing + context window, fuzzy search, set as default
- **Help overlay**; Keyboard shortcut reference, slash command list, getting-started guide
- **FPS overlay**; Real-time FPS counter with frame time histogram, memory usage, GC stats
- **Branding**; keprix logo ASCII art, version info, attribution line (Hermes-derived, keprix-extended)

### Utility displays
- **Thinking indicator**; Spinner animation during reasoning, token count, time elapsed, collapse/expand toggle
- **Message line metadata**; Per-message: model used, token count, latency, tool calls made
- **Queued messages**; Show count of queued messages while agent is busy, send-all button
- **Masked prompt**; For password/API key fields, show `***` with eye toggle to reveal

## Tasks

1. **App chrome**
   - Build `tui/widgets/top_bar.py`; session title, model badge, token counter, clock
   - Build `tui/widgets/status_bar.py`; input mode, gateway status, agent busy/idle
   - Build `tui/widgets/app_layout.py`; resizable three-panel layout (sidebar, chat, details)
   - Add resize handles, collapse/expand animations, persistent panel width preferences

2. **Sidebars and panels**
   - Build `tui/widgets/todo_panel.py`; live todo list with toggle, add, remove, edit
   - Build `tui/widgets/prompts_panel.py`; saved prompt library with search and insert
   - Build `tui/widgets/session_switcher.py`; session list with preview, Ctrl+Tab cycling
   - Build `tui/widgets/details_panel.py`; message metadata, tool trace, API inspector

3. **Overlays**
   - Build `tui/widgets/agents_overlay.py`; sub-agent tree with live status and output preview
   - Build `tui/widgets/skills_hub.py`; skill browser, search, install, enable/disable
   - Build `tui/widgets/plugins_hub.py`; plugin browser, marketplace, configure
   - Build `tui/widgets/model_picker.py`; grouped model list with search and pricing

4. **Utility displays**
   - Build `tui/widgets/thinking_indicator.py`; spinner, token count, time, expand/collapse
   - Build `tui/widgets/message_metadata.py`; per-message model, tokens, latency, tools
   - Build `tui/widgets/queued_messages.py`; queue counter, send-all button

5. **Branding**
   - Update `tui/app.py` startup banner with keprix logo ASCII art
   - Add version info line: "keprix vX.Y.Z; Built on Hermes Agent"
   - Apply keprix color theme consistently across all new widgets via `tui/theme.py`

## Files to create

```
src/keprix/tui/
  theme.py                     - keprix color theme, applied to all widgets
  widgets/
    top_bar.py
    status_bar.py
    app_layout.py
    todo_panel.py
    prompts_panel.py
    session_switcher.py
    details_panel.py
    agents_overlay.py
    skills_hub.py
    plugins_hub.py
    model_picker.py
    thinking_indicator.py
    message_metadata.py
    queued_messages.py
    help_overlay.py             - keyboard shortcuts, slash commands reference

tests/tui/
  test_todo_panel.py
  test_session_switcher.py
  test_skills_hub.py
  test_model_picker.py
  test_app_layout.py
```

## Acceptance criteria

- Top bar shows session title, model name, token usage, and clock
- Todo panel syncs with agent's todo list in real-time
- Session switcher shows all open sessions with Ctrl+Tab cycling
- Skills hub lets the operator browse, install, and enable/disable skills
- Model picker groups models by provider with search and pricing display
- Agent overlay shows sub-agent tree with live status
- Startup banner shows keprix logo in ASCII art with version info
- All panels are collapsible with persistent width preferences
- keprix color theme applied consistently; no Hermes look copied
